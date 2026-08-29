"""
Admin routes: read and replace a unit's COMPOSITION (section T2).

Two endpoints, both admin-only:

    GET  /admin/units/{unit_id}/criteria   the whole shape + lock state
    PUT  /admin/units/{unit_id}/criteria   replace the whole shape

WHY A SEPARATE MODULE FROM `units.py`
-------------------------------------
`units.py` owns a unit's LIFECYCLE - create, assign a lecturer, archive.
This owns its SHAPE. They share a URL prefix and an admin gate and
nothing else, and the composition rules are long enough that folding them
into the lifecycle file would bury both.

WHY A PUT AND NOT PER-ITEM CRUD
-------------------------------
Every composition rule is about the shape as a whole: at most three
items, a 20% cap on quizzes, a 100% budget shared with the tutorial.
Per-item endpoints check each rule against a picture that is momentarily
wrong - swapping a 40% assignment for a 50% one is legal as one act and
illegal in either order as two, so a coordinator would have to make their
unit temporarily invalid to make it valid. A whole-object replace checks
the finished picture once.

THREE REFUSALS, THREE STATUS CODES
----------------------------------
    400  the shape breaks a composition rule   (CompositionError)
    409  the unit's shape is locked            (ShapeLockedError, T1)
    422  the payload is malformed              (pydantic)

The form does something different with each: a message under a field, an
unlock dialog, and a bug report respectively. Collapsing any two of them
forces the client to pattern-match on English error text.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.enums import UserRole
from app.models.unit import Unit
from app.models.user import User
from app.schemas.unit_shape import UnitShapeIn, UnitShapeOut
from app.services import audit_service, unit_composition

router = APIRouter(
    prefix="/admin/units/{unit_id}/criteria",
    tags=["Admin - Unit Composition"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


def _get_unit_or_404(db: Session, unit_id: int) -> Unit:
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
        )
    return unit


@router.get("", response_model=UnitShapeOut)
def get_unit_criteria(unit_id: int, db: Session = Depends(get_db)):
    """
    The unit's assessments, its tutorial setting, the derived pass marks,
    the running total and the lock state - in ONE request.

    Deliberately one call rather than a shape call plus a lock call. The
    form cannot render a single field correctly without both: a disabled
    input and an editable one are not the same screen, and fetching them
    separately means a first paint that is wrong.
    """
    unit = _get_unit_or_404(db, unit_id)
    return unit_composition.get_unit_shape(db, unit)


@router.put("", response_model=UnitShapeOut)
def replace_unit_criteria(
    unit_id: int,
    payload: UnitShapeIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Replace the unit's assessments and tutorial setting.

    Scoped to those two categories: attendance and Moodle are seeded at
    unit creation, carry 55% of the rule blend between them, and are
    never touched here - see `unit_composition.replace_unit_shape`.

    A payload that changes nothing is accepted and writes nothing, even
    while the unit is locked. The setup form GETs the shape and PUTs it
        back, so pressing Save without editing must not consume an admin's
    one-shot unlock window.
    """
    unit = _get_unit_or_404(db, unit_id)

    # Snapshot first: a whole-object replace leaves nothing behind to
    # compare against, and "the shape changed" is not a fact anybody can
    # act on six weeks later.
    before = audit_service.shape_snapshot(unit_composition.get_unit_shape(db, unit))

    items = [item.model_dump() for item in payload.assessments]

    try:
        shape = unit_composition.replace_unit_shape(
            db, unit, items, payload.tutorials_enabled
        )
    except unit_composition.ShapeLockedError as exc:
        # 409, not 400: the shape is legal and would have been accepted
        # yesterday. It is the unit's state that refuses it, so the
        # client should offer an unlock rather than a corrected number.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    except unit_composition.CompositionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )

    after = audit_service.shape_snapshot(shape)
    summary = audit_service.describe_shape_change(before, after)
    # A payload that changes nothing is accepted and writes nothing -
    # the setup form GETs the shape and PUTs it back, and pressing Save
    # without editing must not consume an unlock window. It must not
    # produce an audit row either, for the same reason.
    if summary:
        audit_service.record(
            db,
            action=audit_service.CRITERIA_SHAPE_REPLACED,
            actor=current_user,
            unit=unit,
            entity_type="unit",
            entity_id=unit.id,
            summary=f"{summary} Unit {unit.unit_code}.",
            before=before,
            after=after,
            request=request,
        )

    db.commit()

    # Re-read after the commit rather than returning the staged dict:
    # new rows only have their ids once the flush lands, and a form that
    # PUTs back an id it never received would create duplicates on the
    # next save.
    return unit_composition.get_unit_shape(db, unit)