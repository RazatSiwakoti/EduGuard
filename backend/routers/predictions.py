from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ML.predictor import predict_risk


router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
)


class PredictionInput(BaseModel):
    moodle_login_count: float = Field(ge=0)
    attendance_pct: float = Field(ge=0, le=100)
    attendance_trend: float
    tut_completion_pct: float = Field(ge=0, le=100)
    tut_trend: float
    assessment_avg_pct: float = Field(ge=0, le=100)


@router.post("/")
def create_prediction(payload: PredictionInput):
    try:
        result = predict_risk(payload.model_dump())

        return {
            "input": payload.model_dump(),
            **result,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction error: {error}",
        )