"""
Pydantic schemas for Unit management: create, update, assign a lecturer,
and the response shape returned to the client.
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.auth import UserOut
from app.services.class_code import CLASS_TYPES

#: A Literal rather than a plain str, so an unknown class type is a 422
#: from pydantic before it ever reaches the service. The vocabulary is
#: locked deliberately - see app/services/class_code.py.
ClassTypeIn = Literal["LA", "NCLA"]


class UnitCreate(BaseModel):
    unit_code: str = Field(..., min_length=1, max_length=50)
    unit_name: str = Field(..., min_length=1, max_length=255)
    start_date: Optional[date] = None
    year: int = Field(..., ge=2000, le=2100)
    teaching_period: str = Field(..., min_length=1, max_length=20)
    level: Optional[str] = Field(None, max_length=20)  # "bachelor" / "master"
    lecturer_id: Optional[int] = None

    #: Which of the subject's parallel classes this is. Both optional:
    #: a unit with no class split is valid and is what every existing
    #: row is. Composed into `Unit.class_code` by the service, never
    #: stored as two fields - see app/services/class_code.py.
    class_type: Optional[ClassTypeIn] = None
    class_number: Optional[int] = Field(None, ge=1, le=99)


class UnitUpdate(BaseModel):
    unit_name: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    level: Optional[str] = Field(None, max_length=20)

    #: Editable after creation. A class code is a LABEL, not a rule - it
    #: changes nothing about how a student is scored - so the same
    #: principle the criteria shape lock uses applies: a rename is always
    #: allowed. Uniqueness is still enforced, because two classes cannot
    #: both be LA1.
    #:
    #: `class_number` alone is meaningless without `class_type`, so the
    #: route requires them to be sent together.
    class_type: Optional[ClassTypeIn] = None
    class_number: Optional[int] = Field(None, ge=1, le=99)


class UnitAssignLecturer(BaseModel):
    lecturer_id: int


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    #: The SUBJECT, e.g. "ICT730". Not unique on its own - several
    #: classes of one subject share it, which is what makes grouping
    #: them possible.
    unit_code: str
    #: "LA1" | "NCLA" | "" for no class split.
    class_code: str = ""
    #: Derived from class_code for the edit form.
    class_type: Optional[str] = None
    class_number: Optional[int] = None
    #: What a human calls this offering: "ICT730LA1", or "ICT730" when
    #: there is no class split. THIS is what the UI prints.
    full_code: str = ""
    unit_name: str
    start_date: Optional[date] = None
    year: Optional[int] = None
    teaching_period: Optional[str] = None
    level: Optional[str] = None
    lecturer_id: Optional[int] = None
    status: str
    is_active: bool
    lecturer: Optional[UserOut] = None
     # Computed on the model itself, not stored - see Unit.enrolled_count.
    enrolled_count: int

