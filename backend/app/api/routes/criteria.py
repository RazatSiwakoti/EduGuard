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

  400  the value is not permitted        (D1 - fix the number)
  409  the unit's shape is locked        (T1 - unlock, or leave it)
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
from app.schemas.unit_shape import LecturerUnitShapeOut, ThresholdUpdateIn
from app.services import criteria_service, unit_composition

router = APIRouter(prefix="/units/{unit_id}/criteria", tags=["Criteria"])


def _locked(exc: unit_composition.ShapeLockedError) -> HTTPException:
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
# first does NOT fall through - it fails validation and returns 422.
# ---------------------------------------------------------------------

@router.get("/lock-state", response_model=LockStateOut)
def get_lock_state(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER, UserRole.ADMIN)),
):
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
    unit = _get_unit_or_404(db, unit_id)
    return unit_composition.unlock_preview(db, unit)


@router.post("/unlock", response_model=UnlockResultOut)
def unlock_criteria(
    unit_id: int,
    payload: UnlockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    unit = _get_unit_or_404(db, unit_id)

    try:
        result = unit_composition.unlock_shape(
            db, unit, payload.unit_code, actor_id=current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db.commit()
    return result


# ---------------------------------------------------------------------
# The lecturer's threshold bar (section T4)
#
# Both literals, so both belong ABOVE `/{criteria_id}` for the same
# reason T1's do - see the note there.
# ---------------------------------------------------------------------

@router.get("/shape", response_model=LecturerUnitShapeOut)
def get_unit_shape_for_lecturer(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER, UserRole.ADMIN)),
):
    """
    What the coordinator set, plus where the lecturer's bars currently
    sit - in ONE request.

    Read-only, and it returns the SAME payload the admin setup endpoint
    does (plus `thresholds`). Building a second, differently-shaped read
    of the same rows is how two screens end up disagreeing about what a
    unit is worth.

    An admin may read it too: they own the shape, and being unable to
    see the bars a lecturer set on a unit they configured would make the
    100% budget half-visible to the person responsible for it.
    """
    unit = _get_unit_or_404(db, unit_id)
    if current_user.role == UserRole.LECTURER:
        _require_assigned_lecturer(unit, current_user)
    return unit_composition.lecturer_threshold_view(db, unit)


@router.patch("/thresholds", response_model=LecturerUnitShapeOut)
def update_unit_thresholds(
    unit_id: int,
    payload: ThresholdUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    """
    Move the pass bar for one or both adjustable categories.

    THE SHAPE LOCK IS DELIBERATELY NOT CONSULTED HERE. A unit is locked
    exactly when marks have been imported or an analysis has run - which
    is exactly when a lecturer looks at their at-risk list and decides
    the bar is wrong. Gating the slider on the lock would make it
    editable only on units where it changes nothing anyone can see. The
    long note in `unit_composition` sets out why that is safe: a shape
    change makes a stored score MEAN something else, a bar change only
    moves the line drawn through scores that stay exactly where they
    are.

    It does mark analyses stale, through T1's existing timestamp, so the
    report and the PDF both say "re-run the analysis" without a second
    mechanism being invented for it.

    Admin-excluded on purpose: an admin's own path to these numbers is
    the setup screen, and widening this role check is section T5's
    problem, with its tenant-isolation retest attached.
    """
    unit = _get_unit_or_404(db, unit_id)
    _require_assigned_lecturer(unit, current_user)

    try:
        view = unit_composition.apply_threshold_changes(
            db, unit, payload.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        # Covers ThresholdError AND the ValueError D1's
        # `validate_lecturer_threshold` raises. Both are "that number is
        # not allowed", both render 400, and the form prints either one
        # under the slider that caused it.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db.commit()
    return unit_composition.lecturer_threshold_view(db, unit)


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

    try:
        unit_composition.assert_may_create_criteria(db, unit)
    except unit_composition.ShapeLockedError as exc:
        raise _locked(exc)

    try:
        criteria_service.assert_lecturer_may_create(data)
    except ValueError as exc:
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

    # SECTION T4: threshold, and nothing else.
    #
    # Checked FIRST, ahead of the shape lock, and the order is the
    # honest one. "You may never set this field" is permanent; "the unit
    # is locked" is timing. Reporting the lock first would tell a
    # lecturer an administrator could unlock the unit and let them
    # change a weight, which is not true and never will be.
    try:
        criteria_service.assert_lecturer_edits_only_threshold(update_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Compared BEFORE the setattr loop, while `criteria` still holds its
    # stored value - afterwards every change looks like a no-op.
    effective = unit_composition.effective_changes(criteria, update_data)

    try:
        criteria_service.assert_lecturer_may_update(criteria, update_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    for field, value in update_data.items():
        setattr(criteria, field, value)

    # NO LOCK GUARD AND NO `record_criteria_write` HERE, deliberately.
    # The only field this route now accepts is the pass bar, which the
    # shape lock does not govern (see `unit_composition`'s T4 note), so
    # `assert_may_update_criteria` could never refuse anything and
    # `record_criteria_write` could never fire - a guard that cannot
    # trigger is the exact pattern this project has produced nine cases
    # of. A bar change DOES invalidate results, so it marks them stale
    # through the one call that can still do something:
    if "threshold" in effective:
        unit_composition.record_threshold_write(unit)

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