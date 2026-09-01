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
from app.core.teaching import TEACHING_ROLES
from app.core.system_accounts import PLACEHOLDER_USER_EMAIL
from app.services import class_code as class_code_rules, unit_service

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


def _get_assignable_teacher_or_404(db: Session, user_id: int) -> User:
    """
    A real, non-placeholder account that may HOLD a unit.

    Widened in T5 from `role == LECTURER` to LECTURER or ADMIN, so an
    admin can be assigned a unit and become "also a lecturer".

    NOT the same function as app.api.routes.admin._get_lecturer_or_404,
    despite the near-identical body, and the two must NOT be merged.
    That one resolves the TARGET of lecturer account management -
    deactivate, reactivate, delete. Widening it to ADMIN would hand
    every admin a `DELETE /admin/lecturers/{id}` that deletes other
    admins, which is Super Admin's job and nobody else's. The
    duplication is the boundary; this docstring is why it stays.

    Deactivated accounts are deliberately still assignable: a unit
    outlives a staff account being switched off for a semester, and
    refusing the assignment here would leave the unit orphaned instead.
    """
    teacher = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.role.in_(TEACHING_ROLES),
            User.email != PLACEHOLDER_USER_EMAIL,
        )
        .first()
    )
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No lecturer or admin account with that id",
        )
    return teacher


# -------------------------
# CREATE UNIT
# -------------------------
@router.post("", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
def create_unit(payload: UnitCreate, db: Session = Depends(get_db)):
    # 400, not 422: the two fields are individually valid and their
    # COMBINATION is what fails ("NCLA classes are not numbered"). A 422
    # would send the client hunting for a malformed field.
    try:
        class_code = class_code_rules.compose(payload.class_type, payload.class_number)
    except class_code_rules.ClassCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Uniqueness is on (unit_code, year, teaching_period, class_code) -
    # the same subject is taught every semester AND more than once
    # within one, so the class is part of the identity.
    existing = (
        db.query(Unit)
        .filter(
            Unit.unit_code == payload.unit_code,
            Unit.year == payload.year,
            Unit.teaching_period == payload.teaching_period,
            Unit.class_code == class_code,
        )
        .first()
    )
    if existing:
        # The message names the class, because "this unit already
        # exists" in front of a coordinator who is deliberately creating
        # a SECOND class of the same subject reads as a bug in the
        # system rather than a duplicate they created.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{class_code_rules.full_code(payload.unit_code, class_code)} already "
                f"exists for {payload.teaching_period} {payload.year}."
                + ("" if class_code else " Give this one a class code (LA1, LA2, NCLA) "
                                          "to run it alongside the existing one.")
            ),
        )

    new_unit = Unit(
        unit_code=payload.unit_code,
        unit_name=payload.unit_name,
        start_date=payload.start_date,
        year=payload.year,
        teaching_period=payload.teaching_period,
        level=payload.level,
        class_code=class_code,
    )

    if payload.lecturer_id is not None:
        _get_assignable_teacher_or_404(db, payload.lecturer_id)
        unit_service.assign_lecturer(db, new_unit, payload.lecturer_id)

    db.add(new_unit)
    db.flush()
    unit_service.seed_default_criteria(db, new_unit)
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
# UPDATE UNIT (unit_name / start_date / level)
# -------------------------
@router.patch("/{unit_id}", response_model=UnitOut)
def update_unit(unit_id: int, payload: UnitUpdate, db: Session = Depends(get_db)):
    unit = _get_unit_or_404(db, unit_id)

    # exclude_unset: only fields actually sent in the request get applied -
    # a PATCH with just unit_name must never null out start_date.
    update_data = payload.model_dump(exclude_unset=True)

    # The class is composed, not assigned. Pulled out of update_data
    # first so the generic setattr loop below never writes `class_type`
    # onto the model, where it is a read-only derived property.
    sent_type = "class_type" in update_data
    sent_number = "class_number" in update_data
    class_type = update_data.pop("class_type", None)
    class_number = update_data.pop("class_number", None)

    if sent_type or sent_number:
        # A number without its type is a half-sent form. Composing it
        # would either drop the number silently or invent a type, and
        # both leave the coordinator believing something that is not so.
        if sent_number and not sent_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Send class_type together with class_number.",
            )
        try:
            new_class_code = class_code_rules.compose(class_type, class_number)
        except class_code_rules.ClassCodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        if new_class_code != unit.class_code:
            # Checked in the application as well as by the constraint,
            # so the coordinator gets a sentence naming the clash rather
            # than a 500 from an IntegrityError.
            clash = (
                db.query(Unit)
                .filter(
                    Unit.id != unit.id,
                    Unit.unit_code == unit.unit_code,
                    Unit.year == unit.year,
                    Unit.teaching_period == unit.teaching_period,
                    Unit.class_code == new_class_code,
                )
                .first()
            )
            if clash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"{class_code_rules.full_code(unit.unit_code, new_class_code)} "
                        f"already exists for {unit.teaching_period} {unit.year}."
                    ),
                )
            unit.class_code = new_class_code

    unit_service.update_unit(db, unit, update_data)

    db.commit()
    db.refresh(unit)
    return unit


# -------------------------
# ASSIGN LECTURER (overwrites directly)
# -------------------------
@router.patch("/{unit_id}/assign-lecturer", response_model=UnitOut)
def assign_lecturer_to_unit(unit_id: int, payload: UnitAssignLecturer, db: Session = Depends(get_db)):
    unit = _get_unit_or_404(db, unit_id)
    _get_assignable_teacher_or_404(db, payload.lecturer_id)

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