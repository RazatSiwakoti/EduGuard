"""
Lecturer-facing routes - Phase 6.2.

Distinct silo from app.api.routes.admin and app.api.routes.units, which
are both admin-gated. Before this file existed there was no way for a
lecturer to read their OWN units or cohort over HTTP at all: every risk
route was a per-student POST, and the only unit listing lived behind
/admin/units. That gap is what this router closes.

Read-only by design. Nothing here mutates state - running the analysis
stays on the existing /units/{unit_id}/risk/run-analysis endpoint, so
the dashboard can never accidentally trigger a recompute just by being
opened or refreshed.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_teaching_role
from app.database import get_db
from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.assessment_event import AssessmentEvent
from app.models.criteria import Criteria
from app.models.enums import EventSource
from app.models.final_verdicts import FinalVerdict
from app.models.verdict_review import VerdictReview
from app.models.risk_score import RiskScore
from app.models.student_note import StudentNote
from app.models.unit import Unit
from app.models.user import User
from app.services import audit_service
from app.schemas.dashboard import DashboardUnit, LecturerDashboardResponse
from app.services.dashboard_service import (
    DEFAULT_CHECKPOINT_WEEK,
    get_lecturer_dashboard,
    list_lecturer_units,
)
from app.schemas.student_detail import (
    StudentDetailResponse,
    StudentNoteDetail,
    StudentNoteUpdate,
    StudentReviewSubmit,
)
from app.schemas.student_edit import StudentEditPayload

from app.services.student_detail_service import (
    get_student_detail,
    save_student_note,
    submit_student_review,
)
from app.services.ingestion_service import build_assessment_event, validate_score

router = APIRouter(
    prefix="/lecturer",
    tags=["Lecturer - Dashboard"],
    dependencies=[Depends(require_teaching_role())],
)


@router.get("/dashboard", response_model=LecturerDashboardResponse)
def read_lecturer_dashboard(
    checkpoint_week: int = Query(
        default=DEFAULT_CHECKPOINT_WEEK,
        ge=1,
        le=52,
        description="Which checkpoint's risk picture to return. Only week 8 "
        "is populated today, but the parameter exists so multi-checkpoint "
        "analysis needs no API change later.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
):
    """
    Everything the analytics dashboard needs, in one request: the
    lecturer's units, and one flat row per enrolled student per unit
    carrying their latest risk picture and criterion scores.

    Scoped entirely to `current_user` - the lecturer id is taken from
    the validated JWT, never from a query parameter, so there is no way
    to request another lecturer's cohort by tampering with the URL.

    Returns 200 with empty lists (not 404) when the lecturer has no
    units assigned yet. That is a legitimate state for a new account,
    and the frontend renders a proper empty state for it.
    """
    return get_lecturer_dashboard(db, current_user.id, checkpoint_week)

@router.get("/units", response_model=list[DashboardUnit])
def read_lecturer_units(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
):
    """
    Just the units this lecturer is assigned to - no cohort, no scores.

    Every screen outside the dashboard needs this list: the units page,
    the unit switcher, and the import wizard's "which unit am I
    uploading into" context. Those could technically read units off
    /lecturer/dashboard, but that endpoint drags every enrolled student
    and their criterion scores along with it - an expensive payload to
    fetch when all you wanted was a handful of unit codes.

    Reuses DashboardUnit rather than defining a near-identical schema,
    since it already carries exactly these fields.
    """
    return list_lecturer_units(db, current_user.id)

@router.get("/students/{student_id}", response_model=StudentDetailResponse)
def read_student_detail(
    student_id: int = Path(..., ge=1),
    unit_id: int = Query(
        ...,
        ge=1,
        description="Which unit's picture to return. REQUIRED, not optional: "
        "risk is computed per unit, so a student enrolled in two units has "
        "two different verdicts and there is no such thing as their overall "
        "risk. Omitting it would force this endpoint to invent one.",
    ),
    checkpoint_week: int = Query(default=DEFAULT_CHECKPOINT_WEEK, ge=1, le=52),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
):
    """
    Everything the student card renders, in one request.

    Both path and query parameters are attacker-controlled, so ownership
    is re-checked in SQL: the unit must belong to `current_user` and the
    student must be enrolled in it. Either failure returns 404 rather
    than 403 - a 403 would confirm that someone else's unit exists.

    Returns criteria the student has NO data for as well, with a null
    score. That is the whole difference from the dashboard payload, and
    it is what lets the card distinguish "not marked" from "scored zero".
    """
    detail = get_student_detail(
        db, current_user.id, student_id, unit_id, checkpoint_week
    )

    if detail is None:
        raise HTTPException(
            status_code=404,
            detail="No such student in a unit you teach.",
        )

    return detail


@router.put("/students/{student_id}/note", response_model=StudentNoteDetail)
def update_student_note(
    payload: StudentNoteUpdate,
    student_id: int = Path(..., ge=1),
    unit_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
):
    """
    Saves the requesting lecturer's own notes about this student.

    The ONLY write on this router, which is otherwise read-only by
    design. It is safe here because it cannot touch risk data: notes
    live in their own table and no engine reads them. Opening or
    refreshing the card still cannot trigger a recompute.

    PUT rather than POST because it is idempotent - one note per
    lecturer per student per unit, replaced wholesale on each save.

    Notes deliberately do NOT live on FinalVerdict. That table is
    append-only, so a note attached to one verdict would silently vanish
    the next time the analysis was run.
    """
    note = save_student_note(
        db, current_user.id, student_id, unit_id, payload.body
    )

    if note is None:
        raise HTTPException(
            status_code=404,
            detail="No such student in a unit you teach.",
        )

    return note


@router.post("/students/{student_id}/review", response_model=StudentDetailResponse)
def review_student_verdict(
    request: Request,
    payload: StudentReviewSubmit,
    student_id: int = Path(..., ge=1),
    unit_id: int = Query(..., ge=1),
    checkpoint_week: int = Query(default=DEFAULT_CHECKPOINT_WEEK, ge=1, le=52),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
):
    """
    Records this lecturer's decision on the current engine verdict,
    whether or not the engines disagree.

    TAKES NO VERDICT ID. The verdict is resolved server-side from
    (student, unit, checkpoint), because the id the browser is holding
    can be stale: a lecturer opens the card, a colleague clicks "Run
    Analysis", and the id in the page now points at a superseded row.
    Writing a decision there would stamp it onto a verdict nothing
    reads, and the student would stay in the queue with no explanation.

    POST rather than PATCH because this is not an edit. Reviews are
    append-only: submitting again records a NEW decision that supersedes
    the last, which is how a misclick gets corrected while the fact that
    it happened stays on record.

        Returns the full refreshed card payload rather than a bare
    confirmation, so the client re-renders the resolved tier, the new
    history entry and the cleared review prompt from one round trip.
    """
    # STAGED BEFORE THE CALL, and that is deliberate.
    #
    # `submit_student_review` owns its own `db.commit()`. Recording afterwards would put the audit row in a SECOND transaction, so a
    # failure between the two would leave a decision on a student's file with no record of who made it. `audit_service.record` only stages,
    # so staging first means the service's commit carries both - and every path that does not reach that commit (ownership failure,
    # ValueError, an unanalysed student) leaves the row uncommitted and discarded with the session.
    # The consequence is that the summary describes the DECISION the lecturer submitted rather than the tier derived from it. That is
    # arguably the more honest thing to audit: the tier is the system's conclusion, the decision is the human's act.
    unit = db.get(Unit, unit_id)
    student = db.get(Student, student_id)
    audit_service.record(
        db,
        action=audit_service.VERDICT_OVERRIDDEN,
        actor=current_user,
        unit=unit,
        student=student,
        entity_type="final_verdict",
        summary=(
            f"Verdict overridden for {student.name if student else 'a student'} "
            f"in {unit.unit_code if unit else 'a unit'} at week {checkpoint_week}: "
            f"chose {payload.decision}."
        ),
        after={
            "decision": payload.decision,
            "comment": payload.comment,
            "checkpoint_week": checkpoint_week,
        },
        request=request,
    )

    try:
        detail = submit_student_review(
            db,
            current_user.id,
            student_id,
            unit_id,
            payload.decision,
            payload.comment,
            checkpoint_week,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    if detail is None:
        raise HTTPException(
            status_code=404,
            detail="No such student in a unit you teach.",
        )

    return detail


def _owned_enrollment(db: Session, student_id: int, unit_id: int, lecturer_id: int):
    unit = db.query(Unit).filter(Unit.id == unit_id, Unit.lecturer_id == lecturer_id).first()
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student_id, Enrollment.unit_id == unit_id)
        .first()
    )
    return unit, enrollment


@router.patch("/students/{student_id}", response_model=StudentDetailResponse)
def edit_student(
    request: Request,
    payload: StudentEditPayload,
    student_id: int = Path(..., ge=1),
    unit_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
):
    unit, enrollment = _owned_enrollment(db, student_id, unit_id, current_user.id)
    student = db.get(Student, student_id)
    if unit is None or enrollment is None or student is None:
        raise HTTPException(status_code=404, detail="No such student in a unit you teach.")

    before = {
        "name": student.name,
        "email": student.email,
        "program": student.program,
        "gender": student.gender,
        "age": student.age,
        "scores": payload.scores,
    }
    fields = payload.model_dump(exclude_unset=True)
    fields.pop("scores", None)
    for field, value in fields.items():
        setattr(student, field, value)

    criteria = {
        criterion.id: criterion
        for criterion in db.query(Criteria).filter(
            Criteria.unit_id == unit_id,
            Criteria.id.in_(list(payload.scores)),
        ).all()
    }
    unknown = set(payload.scores) - set(criteria)
    if unknown:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Unknown criteria for this unit: {sorted(unknown)}")

    for criteria_id, score in payload.scores.items():
        if score is None:
            continue
        error = validate_score(criteria[criteria_id], score)
        if error:
            db.rollback()
            raise HTTPException(status_code=400, detail=error)
        db.add(
            build_assessment_event(
                student,
                unit_id,
                criteria[criteria_id],
                score,
                EventSource.MANUAL,
                current_user.id,
            )
        )

    audit_service.record(
        db,
        action=audit_service.STUDENT_EDITED,
        actor=current_user,
        unit=unit,
        student=student,
        entity_type="student",
        entity_id=student.id,
        summary=f"Edited student data for {student.name} in {unit.unit_code}.",
        before=before,
        after=payload.model_dump(exclude_unset=True),
        request=request,
    )
    db.commit()
    detail = get_student_detail(db, current_user.id, student_id, unit_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Student detail is unavailable after editing.")
    return detail


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    request: Request,
    student_id: int = Path(..., ge=1),
    unit_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
):
    unit, enrollment = _owned_enrollment(db, student_id, unit_id, current_user.id)
    student = db.get(Student, student_id)
    if unit is None or enrollment is None or student is None:
        raise HTTPException(status_code=404, detail="No such student in a unit you teach.")

    before = {
        "student_id": student.id,
        "student_number": student.student_number,
        "name": student.name,
        "email": student.email,
        "program": student.program,
        "gender": student.gender,
        "age": student.age,
        "unit_id": unit_id,
        "unit_code": unit.unit_code,
    }
    audit_service.record(
        db,
        action=audit_service.STUDENT_DELETED,
        actor=current_user,
        unit=unit,
        student=student,
        entity_type="student",
        entity_id=student.id,
        summary=f"Deleted {student.name} from {unit.unit_code}.",
        before=before,
        request=request,
    )

    db.query(FinalVerdict).filter(
        FinalVerdict.student_id == student_id, FinalVerdict.unit_id == unit_id
    ).delete(synchronize_session=False)
    db.query(VerdictReview).filter(
        VerdictReview.student_id == student_id, VerdictReview.unit_id == unit_id
    ).delete(synchronize_session=False)
    db.query(RiskScore).filter(
        RiskScore.student_id == student_id, RiskScore.unit_id == unit_id
    ).delete(synchronize_session=False)
    db.query(AssessmentEvent).filter(
        AssessmentEvent.student_id == student_id, AssessmentEvent.unit_id == unit_id
    ).delete(synchronize_session=False)
    db.query(StudentNote).filter(
        StudentNote.student_id == student_id, StudentNote.unit_id == unit_id
    ).delete(synchronize_session=False)
    db.delete(enrollment)
    db.flush()
    if not db.query(Enrollment).filter(Enrollment.student_id == student_id).first():
        db.delete(student)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)