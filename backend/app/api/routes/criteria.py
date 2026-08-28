"""
Lecturer routes: manage Criteria for a unit they are assigned to.

Ownership check mirrors app.api.routes.ingestion - a lecturer must own
the specific unit_id in the path, not just hold the Lecturer role.

WHAT A LECTURER MAY WRITE (section D1)
--------------------------------------
Both write paths go through `criteria_service`, which enforces:

  - attendance and Moodle are fixed - refused, not silently ignored
  - assessment and weekly-tutorial thresholds may be LOWERED to their
    floor (45% / 40%) and never raised above the 50% default

Those rules live in one place because create and update used to have no
rules at all: a lecturer could set any threshold, including zero, which
turns "at risk" into whatever they last typed.

THE TWO LIVES OF A UNIT'S SHAPE (section T1)
--------------------------------------------
Every write here also passes `unit_composition`, which refuses a SHAPE
change once real assessment or tutorial results exist, or once an
analysis has produced verdicts. Renames stay allowed in both lives.

Two status codes, deliberately different:

  400  the value is not permitted        (D1 - fix the number)
  409  the unit's shape is locked        (T1 - unlock, or leave it)

They are separate because the UI's response is separate: one is a field
error under an input, the other is an admin unlock flow. Collapsing both
into 400 forces the frontend to pattern-match on English error text.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.criteria import Criteria
from app.models.enums import UserRole
from app.models.unit import Unit
from app.models.user import User
from app.schemas.criteria import (
    CriteriaCreate,
    CriteriaOut,
    CriteriaUpdate,
    LockStateOut,
    UnlockPreviewOut,
    UnlockRequest,
    UnlockResultOut,
)
from app.services import criteria_service, unit_composition

router = APIRouter(prefix="/units/{unit_id}/criteria", tags=["Criteria"])


def _locked(exc: unit_composition.ShapeLockedError) -> HTTPException:
    """
    409, not 400. The payload is well-formed AND permitted - it is the
    unit's state that refuses it, and it would have been accepted
    yesterday. 409 Conflict is what tells the client to offer an unlock
    rather than to correct a field.
    """
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


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


# ---------------------------------------------------------------------
# Lock state, preview, unlock (section T1)
#
# DECLARED BEFORE `/{criteria_id}`, AND THAT IS NOT A STYLE CHOICE.
# FastAPI matches routes in declaration order. `/{criteria_id}` is typed
# `int`, so a request to GET /units/1/criteria/lock-state that reaches it
# first does NOT fall through to the next route - it fails validation and
# returns 422 with a message about an invalid integer. Moving these
# declarations below would break both endpoints in a way that looks like
# a client bug.
# ---------------------------------------------------------------------

@router.get("/lock-state", response_model=LockStateOut)
def get_lock_state(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER, UserRole.ADMIN)),
):
    """
    Read-only: may this unit's criteria be edited, and why not.

    Open to the assigned lecturer as well as an admin. A lecturer whose
    form is about to refuse every save needs to be told why before they
    fill it in, not after.
    """
    unit = _get_unit_or_404(db, unit_id)
    if current_user.role == UserRole.LECTURER:
        _require_assigned_lecturer(unit, current_user)
    return unit_composition.shape_lock_state(db, unit)


@router.get("/unlock-preview", response_model=UnlockPreviewOut)
def get_unlock_preview(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    What unlocking will cost, so the UI can state it BEFORE asking for
    the confirmation rather than after.

    Admin-only, matching the unlock itself: there is no reason to show a
    lecturer the price of a door they cannot open.
    """
    unit = _get_unit_or_404(db, unit_id)
    return unit_composition.unlock_preview(db, unit)


@router.post("/unlock", response_model=UnlockResultOut)
def unlock_criteria(
    unit_id: int,
    payload: UnlockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Opens a one-shot edit window on a locked unit. Admin only.

    The typed unit code is the confirmation. It is checked server-side
    and not merely in the dialog, because a client-side-only confirmation
    protects against a mis-click and nothing else.

    NOTE: this marks NOTHING stale. Staleness lands on the save that
    follows - see `unit_composition.unlock_shape`.
    """
    unit = _get_unit_or_404(db, unit_id)

    try:
        result = unit_composition.unlock_shape(
            db, unit, payload.unit_code, actor_id=current_user.id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )

    db.commit()
    return result


@router.post("", response_model=CriteriaOut, status_code=status.HTTP_201_CREATED)
def create_criteria(
    unit_id: int,
    payload: CriteriaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    data = payload.model_dump()

    # T1 first: "this unit is locked" is a truer explanation than "that
    # threshold is too low" when both are true, and it is the one the
    # coordinator can act on.
    try:
        unit_composition.assert_may_create_criteria(db, unit)
    except unit_composition.ShapeLockedError as exc:
        raise _locked(exc)

    try:
        criteria_service.assert_lecturer_may_create(data)
    except ValueError as exc:
        # 400, not 422: the payload is well-FORMED, it is just not
        # permitted. A 422 would tell the client to fix its shape.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    criteria = Criteria(unit_id=unit_id, **data)
    db.add(criteria)
    unit_composition.record_criteria_write(unit)
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

    # Decided BEFORE the fields are written, while `criteria` still holds
    # its stored values - `effective_changes` compares against them, and
    # after the setattr loop every change would look like a no-op.
    effective = unit_composition.effective_changes(criteria, update_data)
    shape_changed = unit_composition.is_shape_change(effective)

    try:
        unit_composition.assert_may_update_criteria(db, unit, criteria, update_data)
    except unit_composition.ShapeLockedError as exc:
        raise _locked(exc)

    try:
        criteria_service.assert_lecturer_may_update(criteria, update_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    for field, value in update_data.items():
        setattr(criteria, field, value)

    # A rename bumps nothing: it must not mark a single analysis stale,
    # and it must not consume an admin's one-shot unlock window.
    unit_composition.record_criteria_write(unit, shape_changed=shape_changed)
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

    # Covers the soft-delete path too: `delete_or_disable_criteria`
    # DISABLES a criterion that has events attached, and a disabled
    # criterion is dropped from the rule engine's blend and from the
    # report. As far as every score already computed is concerned, that
    # is a deletion.
    try:
        unit_composition.assert_may_delete_criteria(db, unit)
    except unit_composition.ShapeLockedError as exc:
        raise _locked(exc)

    try:
        outcome = criteria_service.delete_or_disable_criteria(db, criteria)
        unit_composition.record_criteria_write(unit)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not delete criteria")

    return {"detail": f"Criteria {criteria_id} {outcome}"}