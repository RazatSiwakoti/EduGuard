"""
Pydantic schemas for Criteria management: create, update, and the response shape returned to the client.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import AssessmentKind, CriteriaCategory


class CriteriaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    weight: float = Field(..., gt=0)
    threshold: float = Field(..., ge=0)
    max_score: float = Field(default=100.0, gt=0)
    category: Optional[CriteriaCategory] = None
    sequence_number: Optional[int] = Field(None, ge=1, le=4)


class CriteriaUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    weight: Optional[float] = Field(None, gt=0)
    threshold: Optional[float] = Field(None, ge=0)
    max_score: Optional[float] = Field(None, gt=0)
    category: Optional[CriteriaCategory] = None
    sequence_number: Optional[int] = Field(None, ge=1, le=4)
    enabled: Optional[bool] = None


class CriteriaOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    unit_id: int
    name: str
    weight: float
    threshold: float
    max_score: float
    category: Optional[CriteriaCategory] = None
    # Section T4. T2 added `kind` to the model and to the admin shape
    # endpoint but not here, so nothing outside the coordinator's setup
    # form could tell a quiz from an assignment - the overview tab, the
    # import wizard and the manual-entry form all read THIS schema.
    # Nullable: every row written before T2 has no kind, and the
    # non-assessment categories never have one.
    kind: Optional[AssessmentKind] = None
    sequence_number: Optional[int] = None
    enabled: bool


# ---------------------------------------------------------------------
# The two lives of a unit's shape (section T1)
# ---------------------------------------------------------------------

class LockStateOut(BaseModel):
    state: str                          # "draft" | "locked"
    locked: bool
    lockable: bool                      # would be locked but for an unlock
    unlock_active: bool
    reasons: list[str] = []
    locking_event_count: int = 0
    verdict_count: int = 0
    criteria_updated_at: Optional[datetime] = None
    criteria_unlocked_at: Optional[datetime] = None


class UnlockPreviewOut(LockStateOut):
    """What an unlock will cost, so the UI can state it BEFORE asking."""

    unit_code: str
    verdicts_currently_valid: int = 0
    verdicts_already_stale: int = 0
    students_affected: int = 0
    consequence: str


class UnlockRequest(BaseModel):
    unit_code: str = Field(..., min_length=1, max_length=64)


class UnlockResultOut(LockStateOut):
    unlocked: bool
    detail: str