"""
Pydantic schemas for Criteria management: create, update, and the
response shape returned to the client.
"""

from typing import Optional
from pydantic import BaseModel, Field


class CriteriaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    weight: float = Field(..., gt=0)
    threshold: float = Field(..., ge=0)
    max_score: float = Field(default=100.0, gt=0)


class CriteriaUpdate(BaseModel):
    """Partial update - unit_id is never editable here; a Criteria
    belongs permanently to the unit it was created under."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    weight: Optional[float] = Field(None, gt=0)
    threshold: Optional[float] = Field(None, ge=0)
    max_score: Optional[float] = Field(None, gt=0)
    enabled: Optional[bool] = None


class CriteriaOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    unit_id: int
    name: str
    weight: float
    threshold: float
    max_score: float
    enabled: bool