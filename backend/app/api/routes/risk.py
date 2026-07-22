"""
Risk scoring routes - Phase 5.2. Rule-based engine only for now; ML and
hybrid reconciliation land in later steps of this phase.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.enums import UserRole
from app.models.unit import Unit
from app.models.student import Student
from app.models.user import User
from app.services.rule_score_service import compute_and_stage_rule_score
from app.services.ml_score_service import compute_and_stage_ml_score
from app.models.final_verdicts import FinalVerdict
from app.services.final_verdict_service import compute_and_stage_final_verdict

router = APIRouter(prefix="/units/{unit_id}/students/{student_id}/risk", tags=["Risk Scoring"])


def _get_unit_or_404(db: Session, unit_id: int) -> Unit:
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    return unit


def _get_student_or_404(db: Session, student_id: int) -> Student:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


def _require_assigned_lecturer(unit: Unit, current_user: User) -> None:
    if unit.lecturer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned lecturer for this unit",
        )


@router.post("/rule-based", status_code=status.HTTP_201_CREATED)
def compute_rule_based_risk_score(
    unit_id: int,
    student_id: int,
    checkpoint_week: int = 8,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _get_student_or_404(db, student_id)
    _require_assigned_lecturer(unit, current_user)

    try:
        risk_score = compute_and_stage_rule_score(db, student_id, unit_id, checkpoint_week)
        db.commit()
        db.refresh(risk_score)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Risk scoring failed")

    return {
        "risk_score_id": risk_score.id,
        "risk_level": risk_score.risk_level,
        "risk_score": round(risk_score.risk_score, 4),
        "is_incomplete": risk_score.is_incomplete,
        "missing_criteria": risk_score.missing_criteria,
        "checkpoint_week": risk_score.checkpoint_week,
    }



@router.post("/ml-based", status_code=status.HTTP_201_CREATED)
def compute_ml_based_risk_score(
    unit_id: int,
    student_id: int,
    checkpoint_week: int = 8,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _get_student_or_404(db, student_id)
    _require_assigned_lecturer(unit, current_user)

    try:
        risk_score = compute_and_stage_ml_score(db, student_id, unit_id, checkpoint_week)
        db.commit()
        db.refresh(risk_score)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ML risk scoring failed")

    return {
        "risk_score_id": risk_score.id,
        "risk_level": risk_score.risk_level,
        "risk_score": round(risk_score.risk_score, 4),
        "is_incomplete": risk_score.is_incomplete,
        "missing_criteria": risk_score.missing_criteria,
        "checkpoint_week": risk_score.checkpoint_week,
    }


@router.post("/final-verdict", status_code=status.HTTP_201_CREATED)
def compute_final_verdict(
    unit_id: int,
    student_id: int,
    checkpoint_week: int = 8,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _get_student_or_404(db, student_id)
    _require_assigned_lecturer(unit, current_user)

    try:
        verdict = compute_and_stage_final_verdict(db, student_id, unit_id, checkpoint_week)
        db.commit()
        db.refresh(verdict)
    except ValueError as e:
        # Missing an engine's score entirely - a real client error, not a 500
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Final verdict computation failed")

    return {
        "verdict_id": verdict.id,
        "final_tier": verdict.final_tier,
        "requires_review": verdict.requires_review,
        "reason": verdict.reason,
        "rule_score_id": verdict.rule_score_id,
        "ml_score_id": verdict.ml_score_id,
        "checkpoint_week": verdict.checkpoint_week,
    }