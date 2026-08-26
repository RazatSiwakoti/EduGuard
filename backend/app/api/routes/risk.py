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
from app.models.enrollment import Enrollment
from app.services.analysis_service import run_analysis_for_students
from app.schemas.risk import VerdictReviewSubmit, PendingReviewItem, VerdictReviewResult
from app.services.final_verdict_service import submit_review_decision


router = APIRouter(prefix="/units/{unit_id}/students/{student_id}/risk", tags=["Risk Scoring"])


# Separate router since this endpoint is unit-wide, not per-student
unit_router = APIRouter(prefix="/units/{unit_id}/risk", tags=["Risk Scoring"])


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



@unit_router.post("/run-analysis", status_code=status.HTTP_200_OK)
def run_analysis(
    unit_id: int,
    checkpoint_week: int = 8,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    """The 'Run Analysis' refresh button - recomputes rule + ML + hybrid
    for every currently enrolled student in this unit, using whatever
    data currently exists (no new upload required)."""
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    enrollments = db.query(Enrollment).filter(Enrollment.unit_id == unit_id).all()
    student_ids = [e.student_id for e in enrollments]

    if not student_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No enrolled students in this unit")

    try:
        summary = run_analysis_for_students(db, unit_id, student_ids, checkpoint_week)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Analysis run failed")

    return summary


@unit_router.get("/pending-review", response_model=list[PendingReviewItem])
def list_pending_reviews(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    verdicts = (
        db.query(FinalVerdict)
        .filter(FinalVerdict.unit_id == unit_id, FinalVerdict.requires_review == True)  # noqa: E712
        .order_by(FinalVerdict.id)
        .all()
    )

    return [
        PendingReviewItem(
            verdict_id=v.id,
            student_id=v.student_id,
            checkpoint_week=v.checkpoint_week,
            reason=v.reason,
        )
        for v in verdicts
    ]


@unit_router.patch("/verdicts/{verdict_id}/review", response_model=VerdictReviewResult)
def review_verdict(
    unit_id: int,
    verdict_id: int,
    payload: VerdictReviewSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    verdict = db.query(FinalVerdict).filter(FinalVerdict.id == verdict_id).first()
    if not verdict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verdict not found")
    if verdict.unit_id != unit_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verdict does not belong to this unit")

    try:
        updated = submit_review_decision(
            db, verdict_id, current_user.id, payload.review_decision, payload.comment
        )
        
        db.commit()
        db.refresh(updated)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Review submission failed")

    return VerdictReviewResult(
        verdict_id=updated.id,
        final_tier=updated.final_tier,
        requires_review=updated.requires_review,
        reviewed_by=updated.reviewed_by,
        review_decision=updated.review_decision,
        reviewed_at=updated.reviewed_at,
    )