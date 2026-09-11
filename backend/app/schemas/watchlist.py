from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WatchlistChange(BaseModel):
    student_id: int
    unit_id: int
    reason: Optional[str] = None


class WatchlistItem(BaseModel):
    student_id: int
    student_number: str
    student_name: str
    unit_id: int
    unit_code: str
    added_at: Optional[datetime] = None
    reason: Optional[str] = None
