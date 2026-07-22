"""
Final Verdict data-wiring layer - Phase 5.2.

Fetches a student's most recent rule_based and ml_model RiskScore rows,
runs them through hybrid_engine.reconcile(), and stages a FinalVerdict
row. Does NOT commit - the calling route owns the transaction boundary.
"""

from sqlalchemy.orm import Session

from app.models.risk_score import RiskScore
from app.models.final_verdicts import FinalVerdict
from app.services.rule_engine import RiskTier
from app.services.hybrid_engine import reconcile


def get_latest_score(db: Session, student_id: int, unit_id: int, source: str, checkpoint_week: int) -> RiskScore | None:
    """Most recent RiskScore row for this student/unit/checkpoint from
    one specific engine (source='rule_based' or 'ml_model')."""
    return (
        db.query(RiskScore)
        .filter(
            RiskScore.student_id == student_id,
            RiskScore.unit_id == unit_id,
            RiskScore.source == source,
            RiskScore.checkpoint_week == checkpoint_week,
        )
        .order_by(RiskScore.computed_at.desc(), RiskScore.id.desc())
        .first()
    )

def build_reason(rule_score: RiskScore, ml_score: RiskScore, requires_review: bool) -> str:
    """Combines both engines' own stored explanations into one final
    reason. If review is required, that's stated up front."""
    combined = f"{rule_score.explanation or ''} {ml_score.explanation or ''}".strip()
    if requires_review:
        return (
            f"Rule engine ({rule_score.risk_level}) and ML model ({ml_score.risk_level}) "
            f"disagree significantly - needs lecturer review. {combined}"
        ).strip()
    return combined


def compute_and_stage_final_verdict(
    db: Session, student_id: int, unit_id: int, checkpoint_week: int = 8
) -> FinalVerdict:
    """
    Full pipeline: fetch both engines' latest scores -> reconcile ->
    stage a FinalVerdict row. Raises ValueError if either engine hasn't
    scored this student yet - a verdict needs BOTH inputs to exist.
    """
    rule_score = get_latest_score(db, student_id, unit_id, "rule_based", checkpoint_week)
    ml_score = get_latest_score(db, student_id, unit_id, "ml_model", checkpoint_week)

    if not rule_score:
        raise ValueError("No rule_based RiskScore found for this student/unit/checkpoint yet")
    if not ml_score:
        raise ValueError("No ml_model RiskScore found for this student/unit/checkpoint yet")

    hybrid_result = reconcile(RiskTier(rule_score.risk_level), RiskTier(ml_score.risk_level))

    verdict = FinalVerdict(
        student_id=student_id,
        unit_id=unit_id,
        checkpoint_week=checkpoint_week,
        rule_score_id=rule_score.id,
        ml_score_id=ml_score.id,
        final_tier=hybrid_result.final_tier.value if hybrid_result.final_tier else None,
        requires_review=hybrid_result.requires_review,
        reason=build_reason(rule_score, ml_score, hybrid_result.requires_review),
    )
    db.add(verdict)
    return verdict