from typing import Optional
from pydantic import BaseModel


class OutcomeUpdate(BaseModel):
    final_outcome: str
    final_mark: Optional[float] = None


class OutcomeRow(BaseModel):
    enrollment_id: int
    student_id: int
    student_number: str
    student_name: str
    final_outcome: Optional[str] = None
    final_mark: Optional[float] = None


class EvaluationResponse(BaseModel):
    coverage: dict
    confusion_matrix: dict
    metrics: dict
    per_engine_metrics: dict
    lead_time: list
    calibration: list


class BulkOutcomeResult(BaseModel):
    updated: int
    errors: list[dict] = []
