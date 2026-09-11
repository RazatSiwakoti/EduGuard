from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.models.student import Student
from app.models.enrollment import Enrollment
from app.services import audit_service, retention_service

router = APIRouter(
    prefix="/admin",
    tags=["Admin - Retention"],
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)


class PurgeRequest(BaseModel):
    confirmation_count: int = Field(..., ge=0)


@router.get("/retention/preview")
def preview(db: Session = Depends(get_db)):
    rows = retention_service.find_expired(db)
    return {
        "count": len(rows),
        "enrolments": [
            {
                "enrollment_id": row.id,
                "student_id": row.student_id,
                "student_number": row.student.student_number,
                "student_name": row.student.name,
                "unit_id": row.unit_id,
                "unit_code": row.unit.full_code,
            }
            for row in rows
        ],
    }


@router.post("/retention/purge")
def purge(
    payload: PurgeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    rows = retention_service.find_expired(db)
    if payload.confirmation_count != len(rows):
        raise HTTPException(status_code=409, detail="Preview count changed; request a new preview")
    receipts = [retention_service.purge_enrolment(db, row.id) for row in rows]
    audit_service.record(
        db, action=audit_service.DATA_PURGED, actor=current_user,
        summary=f"Retention purge permanently removed {len(receipts)} enrolment(s).",
        entity_type="retention", after={"count": len(receipts)}, request=request,
    )
    db.commit()
    return {"count": len(receipts), "receipts": receipts}


class EraseRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


@router.post("/students/{student_id}/erase")
def erase_student(
    student_id: int,
    payload: EraseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    student = db.query(Student).filter_by(id=student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    rows = db.query(Enrollment).filter_by(student_id=student_id).all()
    receipts = [retention_service.purge_enrolment(db, row.id) for row in rows]
    audit_service.record(
        db, action=audit_service.DATA_PURGED, actor=current_user, student=student,
        summary=f"Student erasure requested: {payload.reason}",
        entity_type="student", entity_id=student_id, after={"reason": payload.reason}, request=request,
    )
    db.commit()
    return {"student_id": student_id, "reason": payload.reason, "purged_enrolments": len(receipts)}
