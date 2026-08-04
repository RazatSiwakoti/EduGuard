"""
Pydantic schemas for the risk-scoring and review-resolution endpoints.
"""

from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel


class VerdictReviewSubmit(BaseModel):
    review_decision: Literal["safe", "low_risk", "high_risk"]


class PendingReviewItem(BaseModel):
    verdict_id: int
    student_id: int
    checkpoint_week: int
    reason: Optional[str]


class VerdictReviewResult(BaseModel):
    verdict_id: int
    final_tier: Optional[str]
    requires_review: bool
    reviewed_by: Optional[int]
    review_decision: Optional[str]
    reviewed_at: Optional[datetime]