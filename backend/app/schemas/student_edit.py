from typing import Optional

from pydantic import BaseModel, Field


class StudentEditPayload(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    program: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=1)
    scores: dict[int, Optional[float]] = Field(default_factory=dict)
