"""
Pydantic schemas for Unit management: create, update, assign a lecturer,
and the response shape returned to the client.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.auth import UserOut


class UnitCreate(BaseModel):
    unit_code: str = Field(..., min_length=1, max_length=50)
    unit_name: str = Field(..., min_length=1, max_length=255)
    start_date: Optional[date] = None
    # Optional at creation time - a unit can be created unassigned and have
    # a lecturer attached later via the dedicated assign endpoint.
    lecturer_id: Optional[int] = None


class UnitUpdate(BaseModel):
    """
    Partial update. unit_code is treated as a stable identifier once
    created, so it isn't editable here, and lecturer assignment has its
    own dedicated endpoint (UnitAssignLecturer) rather than being folded
    into a general-purpose update.
    """
    unit_name: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None


class UnitAssignLecturer(BaseModel):
    lecturer_id: int


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_code: str
    unit_name: str
    start_date: Optional[date] = None
    lecturer_id: Optional[int] = None
    status: str
    is_active: bool
    # Full lecturer details when assigned, None when not - lets the
    # frontend show a name directly instead of just an id.
    lecturer: Optional[UserOut] = None