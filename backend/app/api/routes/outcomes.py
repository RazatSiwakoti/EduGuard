from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.api.routes.ingestion import _parse_upload
from app.core.dependencies import require_teaching_role
from app.database import get_db
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.schemas.evaluation import OutcomeRow, OutcomeUpdate, BulkOutcomeResult
from app.services import audit_service

router = APIRouter(prefix="/lecturer/outcomes", tags=["Outcomes"])
ALLOWED = {"passed", "failed", "withdrawn"}


def _unit(db, unit_id, user):
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(404, "Unit not found")
    if unit.lecturer_id != user.id:
        raise HTTPException(403, "You are not the assigned lecturer for this unit")
    return unit


def _validate(payload):
    if payload.final_outcome not in ALLOWED:
        raise HTTPException(422, "final_outcome must be passed, failed, or withdrawn")
    if payload.final_mark is not None and not 0 <= payload.final_mark <= 100:
        raise HTTPException(422, "final_mark must be between 0 and 100")


@router.patch("/{enrollment_id}", response_model=OutcomeRow)
def record_outcome(enrollment_id: int, payload: OutcomeUpdate, db: Session = Depends(get_db),
                   current_user: User = Depends(require_teaching_role())):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(404, "Enrollment not found")
    unit = _unit(db, enrollment.unit_id, current_user)
    _validate(payload)
    before = {"final_outcome": enrollment.final_outcome, "final_mark": enrollment.final_mark}
    enrollment.final_outcome, enrollment.final_mark = payload.final_outcome, payload.final_mark
    enrollment.outcome_recorded_at, enrollment.outcome_recorded_by = datetime.utcnow(), current_user.id
    audit_service.record(db, action=audit_service.OUTCOME_RECORDED, actor=current_user,
                         unit=unit, student=enrollment.student, entity_type="enrollment",
                         entity_id=enrollment.id, before=before,
                         after={"final_outcome": payload.final_outcome, "final_mark": payload.final_mark})
    db.commit()
    db.refresh(enrollment)
    return OutcomeRow(enrollment_id=enrollment.id, student_id=enrollment.student_id,
                      student_number=enrollment.student.student_number, student_name=enrollment.student.name,
                      final_outcome=enrollment.final_outcome, final_mark=enrollment.final_mark)


@router.post("/bulk", response_model=BulkOutcomeResult)
async def bulk_outcomes(unit_id: int = Form(...), file: UploadFile = File(...),
                        db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    unit = _unit(db, unit_id, current_user)
    df = _parse_upload(file.filename or "upload", await file.read())
    required = {"student_number", "outcome"}
    if not required.issubset({str(c) for c in df.columns}):
        raise HTTPException(422, "CSV must contain student_number,outcome and optional mark")
    errors, updated = [], 0
    for index, row in df.iterrows():
        number = str(row.get("student_number", "")).strip()
        outcome = str(row.get("outcome", "")).strip().lower()
        mark = row.get("mark")
        if outcome not in ALLOWED:
            errors.append({"row": int(index) + 2, "error": "invalid outcome"}); continue
        enrollment = (db.query(Enrollment).join(Student).filter(Student.student_number == number,
                       Enrollment.unit_id == unit_id).first())
        if not enrollment:
            errors.append({"row": int(index) + 2, "error": "student not enrolled"}); continue
        try:
            value = None if mark is None or str(mark).strip() in {"", "nan", "NaN"} else float(mark)
        except (TypeError, ValueError):
            errors.append({"row": int(index) + 2, "error": "invalid mark"}); continue
        if value is not None and not 0 <= value <= 100:
            errors.append({"row": int(index) + 2, "error": "mark must be between 0 and 100"}); continue
        enrollment.final_outcome, enrollment.final_mark = outcome, value
        enrollment.outcome_recorded_at, enrollment.outcome_recorded_by = datetime.utcnow(), current_user.id
        audit_service.record(db, action=audit_service.OUTCOME_RECORDED, actor=current_user, unit=unit,
                             student=enrollment.student, entity_type="enrollment", entity_id=enrollment.id,
                             after={"final_outcome": outcome, "final_mark": value})
        updated += 1
    db.commit()
    return BulkOutcomeResult(updated=updated, errors=errors)


@router.get("/{unit_id}", response_model=list[OutcomeRow])
def list_outcomes(unit_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(require_teaching_role())):
    _unit(db, unit_id, current_user)
    rows = db.query(Enrollment).filter(Enrollment.unit_id == unit_id).all()
    return [OutcomeRow(enrollment_id=e.id, student_id=e.student_id, student_number=e.student.student_number,
                       student_name=e.student.name, final_outcome=e.final_outcome, final_mark=e.final_mark) for e in rows]
