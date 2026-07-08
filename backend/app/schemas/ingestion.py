"""
Pydantic schemas for the ingestion endpoints: bulk upload column mapping,
manual single-student entry, and the response shape reporting per-row
success/failure back to the lecturer.
"""

from typing import Optional
from pydantic import BaseModel


class BulkIngestionMapping(BaseModel):
    """
    Sent as a JSON string in a Form field alongside the uploaded file
    (single-phase, per Phase 4 decision - no separate preview step yet).
    Keys on the right are the lecturer's actual file column headers.
    """
    student_number_col: str
    name_col: str
    email_col: Optional[str] = None
    program_col: Optional[str] = None
    # criteria_id -> column_name
    criteria_column_map: dict[int, str]


class IngestionRowError(BaseModel):
    row: Optional[int] = None
    student_number: Optional[str] = None
    criteria: Optional[str] = None
    reason: str


class IngestionRowWarning(BaseModel):
    row: Optional[int] = None
    student_number: Optional[str] = None
    message: str


class BulkIngestionResult(BaseModel):
    total_rows: int
    rows_with_errors: int
    values_stored: int
    values_failed: int
    batch_id: int
    filename: str
    errors: list[IngestionRowError]
    warnings: list[IngestionRowWarning]


class ManualEntryCreate(BaseModel):
    student_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    program: Optional[str] = None
    # criteria_id -> score
    scores: dict[int, float]


class ManualEntryResult(BaseModel):
    student_number: str
    events_created: int
    errors: list[IngestionRowError]
    warnings: list[IngestionRowWarning]