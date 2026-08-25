"""
Lecturer-facing routes - Phase 6.2.

Distinct silo from app.api.routes.admin and app.api.routes.units, which
are both admin-gated. Before this file existed there was no way for a
lecturer to read their OWN units or cohort over HTTP at all: every risk
route was a per-student POST, and the only unit listing lived behind
/admin/units. That gap is what this router closes.

Read-only by design. Nothing here mutates state - running the analysis
stays on the existing /units/{unit_id}/risk/run-analysis endpoint, so
the dashboard can never accidentally trigger a recompute just by being
opened or refreshed.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.dashboard import DashboardUnit, LecturerDashboardResponse
from app.services.dashboard_service import (
    DEFAULT_CHECKPOINT_WEEK,
    get_lecturer_dashboard,
    list_lecturer_units,
)

router = APIRouter(
    prefix="/lecturer",
    tags=["Lecturer - Dashboard"],
    dependencies=[Depends(require_role(UserRole.LECTURER))],
)


@router.get("/dashboard", response_model=LecturerDashboardResponse)
def read_lecturer_dashboard(
    checkpoint_week: int = Query(
        default=DEFAULT_CHECKPOINT_WEEK,
        ge=1,
        le=52,
        description="Which checkpoint's risk picture to return. Only week 8 "
        "is populated today, but the parameter exists so multi-checkpoint "
        "analysis needs no API change later.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    """
    Everything the analytics dashboard needs, in one request: the
    lecturer's units, and one flat row per enrolled student per unit
    carrying their latest risk picture and criterion scores.

    Scoped entirely to `current_user` - the lecturer id is taken from
    the validated JWT, never from a query parameter, so there is no way
    to request another lecturer's cohort by tampering with the URL.

    Returns 200 with empty lists (not 404) when the lecturer has no
    units assigned yet. That is a legitimate state for a new account,
    and the frontend renders a proper empty state for it.
    """
    return get_lecturer_dashboard(db, current_user.id, checkpoint_week)

@router.get("/units", response_model=list[DashboardUnit])
def read_lecturer_units(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.LECTURER)),
):
    """
    Just the units this lecturer is assigned to - no cohort, no scores.

    Every screen outside the dashboard needs this list: the units page,
    the unit switcher, and the import wizard's "which unit am I
    uploading into" context. Those could technically read units off
    /lecturer/dashboard, but that endpoint drags every enrolled student
    and their criterion scores along with it - an expensive payload to
    fetch when all you wanted was a handful of unit codes.

    Reuses DashboardUnit rather than defining a near-identical schema,
    since it already carries exactly these fields.
    """
    return list_lecturer_units(db, current_user.id)