"""
Pydantic schemas for the ingestion endpoints: bulk upload column mapping,
manual single-student entry, and the response shape reporting per-row
success/failure back to the lecturer.
"""

from typing import Optional
from pydantic import BaseModel


class BulkIngestionMapping(BaseModel):
    student_number_col: str
    name_col: str
    email_col: Optional[str] = None
    program_col: Optional[str] = None
    gender_col: Optional[str] = None
    age_col: Optional[str] = None
    criteria_column_map: dict[int, str]
    weekly_criteria_column_map: dict[int, list[str]] = {}


class FilePreviewResult(BaseModel):
    """
    What the import wizard needs before a lecturer can map anything:
    the file's actual column headers, and enough sample rows to confirm
    they picked the right file and that the columns hold what they
    expect.

    Exists because mapping columns to criteria is impossible until the
    lecturer can SEE their columns, and the /bulk endpoint requires the
    mapping and the file in the same request. Parsing here rather than
    in the browser means .xlsx and .xls work identically to .csv -
    pandas already handles all three, whereas a browser would need a
    large extra library just to read a spreadsheet.

    Nothing is written to the database by a preview. It is a pure
    read-and-describe, so a lecturer can safely try a file, look at it,
    and change their mind.
    """

    filename: str
    columns: list[str]
    total_rows: int
    # Capped server-side - a preview only has to prove the file parsed
    # correctly, and shipping an entire cohort back would defeat the
    # point of a lightweight preview step.
    sample_rows: list[dict]


class IngestionRowError(BaseModel):
    row: Optional[int] = None
    student_number: Optional[str] = None
    criteria: Optional[str] = None
    reason: str


class IngestionRowWarning(BaseModel):
    row: Optional[int] = None
    student_number: Optional[str] = None
    message: str


class StudentAnalysisResult(BaseModel):
    student_id: int
    rule_level: str
    ml_level: str
    final_tier: Optional[str]
    requires_review: bool
    is_incomplete: bool = False
    missing_criteria: list[str] = []


class AnalysisSummary(BaseModel):
    total_students: int
    succeeded: int
    failed: int
    results: list[StudentAnalysisResult]
    errors: list[dict]


class BulkIngestionResult(BaseModel):
    total_rows: int
    rows_with_errors: int
    values_stored: int
    values_failed: int
    batch_id: int
    filename: str
    errors: list[IngestionRowError]
    warnings: list[IngestionRowWarning]
    analysis_summary: Optional[AnalysisSummary] = None


class ManualEntryCreate(BaseModel):
    student_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    program: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None

    # criteria_id -> score, for single-value criteria (Assessment, Moodle)
    scores: dict[int, float] = {}

    # criteria_id -> list of raw weekly values IN WEEK ORDER, for
    # Attendance ("yes"/"no", "1"/"0", "true"/"false" per week - exactly
    # 7 values) or Weekly Tut ("submitted"/"late"/"not_submitted" per
    # week - exactly 6 values, weeks 2-7). Wrong length still computes a
    # percentage but skips the trend value rather than erroring.
    weekly_scores: dict[int, list[str]] = {}


class ManualEntryResult(BaseModel):
    student_number: str
    events_created: int
    errors: list[IngestionRowError]
    warnings: list[IngestionRowWarning]
    analysis_result: Optional[StudentAnalysisResult] = None
    student_created: bool = False
    enrollment_created: bool = False