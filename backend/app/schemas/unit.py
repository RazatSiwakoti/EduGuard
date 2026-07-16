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
    year: int = Field(..., ge=2000, le=2100)
    teaching_period: str = Field(..., min_length=1, max_length=20)
    level: Optional[str] = Field(None, max_length=20)  # "bachelor" / "master"
    lecturer_id: Optional[int] = None


class UnitUpdate(BaseModel):
    unit_name: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    level: Optional[str] = Field(None, max_length=20)


class UnitAssignLecturer(BaseModel):
    lecturer_id: int


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_code: str
    unit_name: str
    start_date: Optional[date] = None
    year: Optional[int] = None
    teaching_period: Optional[str] = None
    level: Optional[str] = None
    lecturer_id: Optional[int] = None
    status: str
    is_active: bool
    lecturer: Optional[UserOut] = None