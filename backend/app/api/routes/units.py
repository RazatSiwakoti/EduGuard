"""
Admin routes: manage Units (create, list, update, assign/unassign a
lecturer, delete-or-archive, reactivate).

Admin-only, same silo as app.api.routes.admin, but kept in its own file
since Unit is a distinct domain from User/Lecturer management.

All state changes that touch lecturer_id/status or the archive decision
go through app.services.unit_service - never duplicated inline here -
so those invariants only exist in one place.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.unit import Unit
from app.models.enums import UserRole
from app.schemas.unit import UnitCreate, UnitUpdate, UnitAssignLecturer, UnitOut
from app.core.dependencies import require_role
from app.core.system_accounts import PLACEHOLDER_USER_EMAIL
from app.services import unit_service

router = APIRouter(
    prefix="/admin/units",
    tags=["Admin - Units"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


def _get_unit_or_404(db: Session, unit_id: int) -> Unit:
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    return unit


def _get_lecturer_or_404(db: Session, lecturer_id: int) -> User:
    """Mirrors app.api.routes.admin's version - a real, non-placeholder
    Lecturer must exist before a unit can be assigned to them."""
    lecturer = (
        db.query(User)
        .filter(
            User.id == lecturer_id,
            User.role == UserRole.LECTURER,
            User.email != PLACEHOLDER_USER_EMAIL,
        )
        .first()
    )
    if not lecturer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecturer not found")
    return lecturer


# -------------------------
# CREATE UNIT
# -------------------------
@router.post("", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
def create_unit(payload: UnitCreate, db: Session = Depends(get_db)):
    existing = db.query(Unit).filter(Unit.unit_code == payload.unit_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit code already in use")

    new_unit = Unit(
        unit_code=payload.unit_code,
        unit_name=payload.unit_name,
        start_date=payload.start_date,
    )

    if payload.lecturer_id is not None:
        _get_lecturer_or_404(db, payload.lecturer_id)
        unit_service.assign_lecturer(db, new_unit, payload.lecturer_id)

    db.add(new_unit)
    db.commit()
    db.refresh(new_unit)
    return new_unit


# -------------------------
# LIST UNITS
# -------------------------
@router.get("", response_model=list[UnitOut])
def list_units(include_inactive: bool = False, db: Session = Depends(get_db)):
    query = db.query(Unit)
    if not include_inactive:
        query = query.filter(Unit.is_active == True)  # noqa: E712
    return query.order_by(Unit.id).all()


# -------------------------
# GET SINGLE UNIT
# -------------------------
@router.get("/{unit_id}", response_model=UnitOut)
def get_unit(unit_id: int, db: Session = Depends(get_db)):
    return _get_unit_or_404(db, unit_id)


# -------------------------
# UPDATE UNIT (unit_name / start_date only)
# -------------------------
@router.patch("/{unit_id}", response_model=UnitOut)
def update_unit(unit_id: int, payload: UnitUpdate, db: Session = Depends(get_db)):
    unit = _get_unit_or_404(db, unit_id)

    # exclude_unset: only fields actually sent in the request get applied -
    # a PATCH with just unit_name must never null out start_date.
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(unit, field, value)

    db.commit()
    db.refresh(unit)
    return unit


# -------------------------
# ASSIGN LECTURER (overwrites directly)
# -------------------------
@router.patch("/{unit_id}/assign-lecturer", response_model=UnitOut)
def assign_lecturer_to_unit(unit_id: int, payload: UnitAssignLecturer, db: Session = Depends(get_db)):
    unit = _get_unit_or_404(db, unit_id)
    _get_lecturer_or_404(db, payload.lecturer_id)

    unit_service.assign_lecturer(db, unit, payload.lecturer_id)
    db.commit()
    db.refresh(unit)
    return unit


# -------------------------
# UNASSIGN LECTURER
# -------------------------
@router.patch("/{unit_id}/unassign-lecturer", response_model=UnitOut)
def unassign_lecturer_from_unit(unit_id: int, db: Session = Depends(get_db)):
    unit = _get_unit_or_404(db, unit_id)

    unit_service.unassign_lecturer(db, unit)
    db.commit()
    db.refresh(unit)
    return unit


# -------------------------
# DELETE (or archive) UNIT
# -------------------------
@router.delete("/{unit_id}")
def delete_unit(unit_id: int, db: Session = Depends(get_db)):
    unit = _get_unit_or_404(db, unit_id)

    try:
        outcome = unit_service.delete_or_archive_unit(db, unit)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not delete unit")

    return {"detail": f"Unit {unit_id} {outcome}"}


# -------------------------
# REACTIVATE ARCHIVED UNIT
# -------------------------
@router.patch("/{unit_id}/reactivate", response_model=UnitOut)
def reactivate_unit(unit_id: int, db: Session = Depends(get_db)):
    unit = _get_unit_or_404(db, unit_id)
    unit.is_active = True
    db.commit()
    db.refresh(unit)
    return unit