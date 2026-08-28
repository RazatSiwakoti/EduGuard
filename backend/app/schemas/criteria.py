"""
Pydantic schemas for Criteria management: create, update, and the response shape returned to the client.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import CriteriaCategory


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
    sequence_number: Optional[int] = None
    enabled: bool


# ---------------------------------------------------------------------
# The two lives of a unit's shape (section T1)
# ---------------------------------------------------------------------

class LockStateOut(BaseModel):
    """
    Whether this unit's criteria may be edited, and why not.

    `reasons` is a list of finished sentences rather than machine codes:
    the UI shows them verbatim, and a client that has to turn an enum
    into a sentence is a second place where the rules get described -
    which is a second place for them to be described wrongly.
    """

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
    """
    The typed confirmation. Named `unit_code` rather than `confirm`
    because the field IS the unit code - a client sending a literal
    "CONFIRM" proves nothing about which unit is open on screen.
    """

    unit_code: str = Field(..., min_length=1, max_length=64)


class UnlockResultOut(LockStateOut):
    unlocked: bool
    detail: str