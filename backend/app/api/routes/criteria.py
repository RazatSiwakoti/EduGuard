"""
Lecturer routes: manage Criteria for a unit they are assigned to.

Ownership check mirrors app.api.routes.ingestion - a lecturer must own
the specific unit_id in the path, not just hold the Lecturer role.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.criteria import Criteria
from app.models.enums import UserRole
from app.models.unit import Unit
from app.models.user import User
from app.schemas.criteria import CriteriaCreate, CriteriaOut, CriteriaUpdate
from app.services import criteria_service

router = APIRouter(prefix="/units/{unit_id}/criteria", tags=["Criteria"])


def _get_unit_or_404(db: Session, unit_id: int) -> Unit:
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    return unit


def _require_assigned_lecturer(unit: Unit, current_user: User) -> None:
    if unit.lecturer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the assigned lecturer for this unit",
        )


def _get_criteria_or_404(db: Session, unit_id: int, criteria_id: int) -> Criteria:
    criteria = (
        db.query(Criteria)
        .filter(Criteria.id == criteria_id, Criteria.unit_id == unit_id)
        .first()
    )
    if not criteria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criteria not found")
    return criteria


@router.post("", response_model=CriteriaOut, status_code=status.HTTP_201_CREATED)
def create_criteria(
    unit_id: int,
    payload: CriteriaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    criteria = Criteria(unit_id=unit_id, **payload.model_dump())
    db.add(criteria)
    db.commit()
    db.refresh(criteria)
    return criteria


@router.get("", response_model=list[CriteriaOut])
def list_criteria(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    return db.query(Criteria).filter(Criteria.unit_id == unit_id).order_by(Criteria.id).all()


@router.get("/{criteria_id}", response_model=CriteriaOut)
def get_criteria(
    unit_id: int,
    criteria_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)
    return _get_criteria_or_404(db, unit_id, criteria_id)


@router.patch("/{criteria_id}", response_model=CriteriaOut)
def update_criteria(
    unit_id: int,
    criteria_id: int,
    payload: CriteriaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)
    criteria = _get_criteria_or_404(db, unit_id, criteria_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(criteria, field, value)

    db.commit()
    db.refresh(criteria)
    return criteria


@router.delete("/{criteria_id}")
def delete_criteria(
    unit_id: int,
    criteria_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)
    criteria = _get_criteria_or_404(db, unit_id, criteria_id)

    try:
        outcome = criteria_service.delete_or_disable_criteria(db, criteria)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not delete criteria")

    return {"detail": f"Criteria {criteria_id} {outcome}"}