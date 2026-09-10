from fastapi import APIRouter, Depends, Query
from app.core.dependencies import require_role
from app.models.enums import UserRole
from app.schemas.evaluation import EvaluationResponse
from app.database import get_db
from app.services import evaluation_service
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/model", tags=["Model evaluation"])


@router.get("", response_model=EvaluationResponse)
def model_performance(
    unit_ids: list[int] | None = Query(default=None),
    checkpoint_week: int = Query(default=8, ge=1, le=52),
    db: Session = Depends(get_db),
    _user=Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    ids = unit_ids or []
    return EvaluationResponse(
        coverage=evaluation_service.coverage(db, ids),
        confusion_matrix=evaluation_service.confusion_matrix(db, ids, checkpoint_week),
        metrics=evaluation_service.metrics(db, ids, checkpoint_week),
        per_engine_metrics=evaluation_service.per_engine_metrics(db, ids, checkpoint_week),
        lead_time=evaluation_service.lead_time(db, ids, checkpoint_week),
        calibration=evaluation_service.calibration(db, ids, checkpoint_week),
    )
