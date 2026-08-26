"""
Per-student detail for the student card (Phase 7.6b).

TENANT ISOLATION IS THE FIRST THING THIS FILE DOES.
Both entry points take `student_id` and `unit_id` straight from the URL,
which means an attacker controls both. The unit is therefore looked up
with `Unit.lecturer_id == lecturer_id` from the validated JWT before
anything else happens, and a unit that does not belong to the caller
returns None - rendered as a 404, not a 403, so the endpoint never
confirms that someone else's unit exists.

Enrolment is checked too. Without it, a lecturer could read any
student's identity by pairing an arbitrary student_id with one of their
own units and getting an empty-but-populated header back.

THE LATEST-ROW PROBLEM applies here exactly as it does on the dashboard:
FinalVerdict, RiskScore and AssessmentEvent are all append-only. This
module works on ONE student, so it takes the latest row with
`order_by(...).limit(1)` per lookup rather than DISTINCT ON - the effect
is identical and the intent is more obvious at this scale. Engine scores
are still loaded BY FOREIGN KEY off the verdict, never by "latest score
for this student", for the same reason dashboard_service does it: a
re-run whose verdict step failed would otherwise show a rule tier and a
final tier that came from different runs.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment_event import AssessmentEvent
from app.models.criteria import Criteria
from app.models.enrollment import Enrollment
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.student_note import StudentNote
from app.models.unit import Unit
from app.services.dashboard_service import DEFAULT_CHECKPOINT_WEEK
from app.models.user import User
from app.models.verdict_review import VerdictReview
from app.services.final_verdict_service import record_review


def _owned_unit(db: Session, unit_id: int, lecturer_id: int) -> Optional[Unit]:
    """
    The unit, but only if this lecturer teaches it.

    Anchored on lecturer_id from the JWT, never from a parameter. Every
    other query in this module hangs off the result, so one failed check
    here closes the whole endpoint.
    """
    stmt = select(Unit).where(Unit.id == unit_id, Unit.lecturer_id == lecturer_id)
    return db.execute(stmt).scalars().first()


def _enrolled(db: Session, student_id: int, unit_id: int) -> Optional[Enrollment]:
    """The enrolment row, or None if this student is not in this unit."""
    stmt = select(Enrollment).where(
        Enrollment.student_id == student_id, Enrollment.unit_id == unit_id
    )
    return db.execute(stmt).scalars().first()


def _latest_verdict(
    db: Session, student_id: int, unit_id: int, checkpoint_week: int
) -> Optional[FinalVerdict]:
    """
    The most recent verdict for this student at this checkpoint.

    Ties break on id DESC as well as created_at, because two runs inside
    the same second would otherwise be ordered arbitrarily - id is
    monotonic and never null.
    """
    stmt = (
        select(FinalVerdict)
        .where(
            FinalVerdict.student_id == student_id,
            FinalVerdict.unit_id == unit_id,
            FinalVerdict.checkpoint_week == checkpoint_week,
        )
        .order_by(FinalVerdict.created_at.desc().nullslast(), FinalVerdict.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _latest_events(
    db: Session, student_id: int, unit_id: int
) -> dict[int, AssessmentEvent]:
    """
    This student's current value for each criterion, keyed by criteria_id.

    AssessmentEvent is immutable - a corrected mark is a new row - so
    "current" means the latest by date. No checkpoint filter: raw events
    are not stamped with one, the checkpoint belongs to the SCORE
    derived from them.
    """
    stmt = (
        select(AssessmentEvent)
        .where(
            AssessmentEvent.student_id == student_id,
            AssessmentEvent.unit_id == unit_id,
        )
        .order_by(
            AssessmentEvent.date.desc().nullslast(), AssessmentEvent.id.desc()
        )
    )

    latest: dict[int, AssessmentEvent] = {}
    for event in db.execute(stmt).scalars().all():
        # Rows arrive newest first, so the first one seen per criterion
        # is the current one and later rows are superseded history.
        latest.setdefault(event.criteria_id, event)
    return latest


def _review_history(
    db: Session, student_id: int, unit_id: int, checkpoint_week: int
) -> list[dict]:
    """
    Every decision recorded for this student in this unit, newest first.

    verdict_reviews is append-only, so a lecturer who changed their mind
    leaves two rows and both are returned. Showing only the current one
    would hide that a decision was revised, which is precisely what an
    audit of an early-warning system wants to see.

    The reviewer's name is joined rather than sent as a bare user id: a
    unit can have had more than one lecturer over time, and "resolved by
    7" tells the reader nothing.
    """
    stmt = (
        select(VerdictReview, User.full_name)
        .join(User, User.id == VerdictReview.reviewed_by, isouter=True)
        .where(
            VerdictReview.student_id == student_id,
            VerdictReview.unit_id == unit_id,
            VerdictReview.checkpoint_week == checkpoint_week,
        )
        .order_by(VerdictReview.created_at.desc(), VerdictReview.id.desc())
    )

    return [
        {
            "id": review.id,
            "decision": review.decision,
            "comment": review.comment,
            "rule_tier": review.rule_tier,
            "ml_tier": review.ml_tier,
            "reviewed_by": review.reviewed_by,
            "reviewer_name": reviewer_name,
            "created_at": review.created_at,
        }
        for review, reviewer_name in db.execute(stmt).all()
    ]

def _engine_payload(score: Optional[RiskScore], score_kind: str) -> Optional[dict]:
    """
    One engine's verdict, or None when no score row was found.

    `score_kind` is passed in rather than inferred, because the number in
    `RiskScore.risk_score` means two different things depending on which
    engine wrote it - a weighted badness score for the rule engine, a
    class probability for the ML model. The frontend needs to be told
    which, or it will label a confidence figure as a risk score.
    """
    if score is None:
        return None

    return {
        "tier": score.risk_level,
        "score": score.risk_score,
        "score_kind": score_kind,
        "is_incomplete": bool(score.is_incomplete),
        "missing_criteria": score.missing_criteria,
        "explanation": score.explanation,
        "computed_at": score.computed_at,
    }


def get_student_detail(
    db: Session,
    lecturer_id: int,
    student_id: int,
    unit_id: int,
    checkpoint_week: int = DEFAULT_CHECKPOINT_WEEK,
) -> Optional[dict]:
    """
    The full picture for one student in one unit, or None if the caller
    does not teach that unit or the student is not enrolled in it.
    """
    unit = _owned_unit(db, unit_id, lecturer_id)
    if unit is None:
        return None

    enrollment = _enrolled(db, student_id, unit_id)
    if enrollment is None:
        return None

    student = db.get(Student, student_id)
    if student is None:
        return None

    verdict = _latest_verdict(db, student_id, unit_id, checkpoint_week)

    rule_score = db.get(RiskScore, verdict.rule_score_id) if verdict else None
    ml_score = db.get(RiskScore, verdict.ml_score_id) if verdict else None

    events = _latest_events(db, student_id, unit_id)

    criteria_stmt = (
        select(Criteria)
        .where(Criteria.unit_id == unit_id, Criteria.enabled.is_(True))
        .order_by(Criteria.id)
    )

    criteria_payload = []
    for criterion in db.execute(criteria_stmt).scalars().all():
        event = events.get(criterion.id)

        criteria_payload.append(
            {
                "criteria_id": criterion.id,
                "name": criterion.name,
                "category": criterion.category.value if criterion.category else None,
                "threshold": criterion.threshold,
                "max_score": criterion.max_score,
                # THE DIFFERENCE FROM THE DASHBOARD PAYLOAD: a criterion
                # with no event is still returned, with a null score,
                # instead of being omitted. "Not marked" is exactly what
                # the card exists to show.
                "score": event.score if event else None,
                "trend_value": event.trend_value if event else None,
                "weekly_values": event.weekly_values if event else None,
                "recorded_at": event.date if event else None,
            }
        )

    note = _get_note_row(db, student_id, unit_id, lecturer_id)

    return {
        "student_id": student.id,
        "student_number": student.student_number,
        "name": student.name,
        "email": student.email,
        "program": student.program,
        "unit_id": unit.id,
        "unit_code": unit.unit_code,
        "unit_name": unit.unit_name,
        "enrolled_at": enrollment.enrollment_date,
        "checkpoint_week": checkpoint_week,
        "analysed": verdict is not None,
        "final_tier": verdict.final_tier if verdict else None,
        "requires_review": verdict.requires_review if verdict else False,
        "reason": verdict.reason if verdict else None,
        "computed_at": verdict.created_at if verdict else None,
        "rule": _engine_payload(rule_score, "badness"),
        "ml": _engine_payload(ml_score, "confidence"),
        "criteria": criteria_payload,
        "note": (
            {"body": note.body, "updated_at": note.updated_at} if note else None
        ),
        "verdict_id": verdict.id if verdict else None,
        # Set whether the decision was submitted against THIS verdict or
        # carried forward onto it from an earlier run. Either way a human
        # stands behind the tier, and the card says so - a carried-forward
        # review that rendered as an ordinary engine result would make
        # the system look more automated than it is.
        "applied_review_id": verdict.review_id if verdict else None,
        "review_history": _review_history(db, student_id, unit_id, checkpoint_week),
    }


def _get_note_row(
    db: Session, student_id: int, unit_id: int, lecturer_id: int
) -> Optional[StudentNote]:
    """This lecturer's note row for this student in this unit, if any."""
    stmt = select(StudentNote).where(
        StudentNote.student_id == student_id,
        StudentNote.unit_id == unit_id,
        StudentNote.lecturer_id == lecturer_id,
    )
    return db.execute(stmt).scalars().first()


def save_student_note(
    db: Session, lecturer_id: int, student_id: int, unit_id: int, body: str
) -> Optional[dict]:
    """
    Creates or updates the requesting lecturer's note.

    UPDATES IN PLACE, which is a deliberate exception to this project's
    append-only rule. Raw observations must never be rewritten; a
    person's own working notes are theirs to edit, and versioning them
    would give a lecturer no way to fix a typo.

    Scoped to the caller's own row, so two lecturers teaching the same
    unit cannot overwrite each other and one lecturer's private notes
    never surface to a colleague.

    Returns None on the same ownership failures as get_student_detail,
    so a write can never reach a unit the caller does not teach.
    """
    if _owned_unit(db, unit_id, lecturer_id) is None:
        return None
    if _enrolled(db, student_id, unit_id) is None:
        return None

    note = _get_note_row(db, student_id, unit_id, lecturer_id)

    if note is None:
        note = StudentNote(
            student_id=student_id,
            unit_id=unit_id,
            lecturer_id=lecturer_id,
            body=body,
        )
        db.add(note)
    else:
        note.body = body

    db.commit()
    db.refresh(note)

    return {"body": note.body, "updated_at": note.updated_at}

def submit_student_review(
    db: Session,
    lecturer_id: int,
    student_id: int,
    unit_id: int,
    decision: str,
    comment: Optional[str],
    checkpoint_week: int = DEFAULT_CHECKPOINT_WEEK,
) -> Optional[dict]:
    """
    Records a decision on this student's latest verdict.

    Resolves the verdict SERVER-SIDE from (student, unit, checkpoint)
    rather than taking a verdict id from the caller. Two reasons:

      1. The client's verdict id can be stale. A lecturer opens the card,
         a colleague clicks "Run Analysis", and the id in the browser now
         points at a superseded row - writing to it would stamp a
         decision onto a verdict nothing reads.
      2. A verdict id from the URL is an object reference the caller
         controls. Deriving it from ids already checked for ownership
         removes a whole class of cross-tenant write.

    Returns None on the same ownership failures as get_student_detail,
    so a decision can never land on a unit the caller does not teach.
    """
    if _owned_unit(db, unit_id, lecturer_id) is None:
        return None
    if _enrolled(db, student_id, unit_id) is None:
        return None

    verdict = _latest_verdict(db, student_id, unit_id, checkpoint_week)
    if verdict is None:
        raise ValueError(
            "This student has not been analysed yet - there is no verdict to review."
        )

    # A verdict the engines agreed on has nothing to resolve. Re-reviewing
    # one that a human already resolved IS allowed - that is how a
    # misclick gets corrected.
    if not verdict.requires_review and verdict.review_id is None:
        raise ValueError(
            "The engines agreed on this student - there is no disagreement to resolve."
        )

    record_review(
        db,
        student_id,
        unit_id,
        checkpoint_week,
        lecturer_id,
        decision,
        comment,
        verdict,
    )
    db.commit()

    return get_student_detail(db, lecturer_id, student_id, unit_id, checkpoint_week)