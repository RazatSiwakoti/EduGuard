"""
FinalVerdict - Phase 5.2

Stores the hybrid layer's reconciled decision for one student/unit/
checkpoint, built from a pair of RiskScore rows (one rule_based, one
ml_model). Kept separate from RiskScore because a verdict carries
different concerns entirely - review status, who reviewed it, when -
that don't belong on an immutable raw engine output.

final_tier is NULL when requires_review is True: a genuine safe-vs-
high_risk disagreement gets NO automatic verdict until a lecturer
resolves it - this is intentional, not a bug.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class FinalVerdict(Base):
    __tablename__ = "final_verdicts"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    checkpoint_week = Column(Integer, nullable=False, default=8)

    rule_score_id = Column(Integer, ForeignKey("risk_scores.id"), nullable=False)
    ml_score_id = Column(Integer, ForeignKey("risk_scores.id"), nullable=False)

    # NULL when requires_review=True - no automatic verdict was reached.
    final_tier = Column(String, nullable=True)
    requires_review = Column(Boolean, nullable=False, default=False)

    # Plain-language explanation for the lecturer - populated from the
    # rule engine's per-criterion breakdown for now; SHAP output gets
    # blended in here once the ML engine exists.
    reason = Column(String, nullable=True)

    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_decision = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    student = relationship("Student")
    unit = relationship("Unit")
    rule_score = relationship("RiskScore", foreign_keys=[rule_score_id])
    ml_score = relationship("RiskScore", foreign_keys=[ml_score_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])