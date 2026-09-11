"""
Who is "also a lecturer" — T5.

One module because the question is asked in three unrelated places and
they must never disagree:

  * `app.core.dependencies.require_teaching_role` — may this account
    reach a lecturer-facing endpoint at all?
  * `app.api.routes.units` — may this account be ASSIGNED a unit?
  * `app.api.routes.auth` — should this account's browser render the
    lecturer navigation?

Razat's rule is that an admin is also a lecturer exactly when they hold
at least one active unit. Deliberately NOT a new column or a new role:
the assignment already exists in `units.lecturer_id`, and a second
place to record the same fact is a second place for it to go stale the
moment a unit is archived.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.unit import Unit
from app.models.user import User

# Roles that may hold a unit, and therefore may use the lecturer
# surface. SUPER_ADMIN is deliberately absent: a super admin manages
# admins, units are never assigned to one, so granting the role would
# only ever produce an empty dashboard behind a nav item.
TEACHING_ROLES: tuple[UserRole, ...] = (UserRole.LECTURER, UserRole.ADMIN)


def holds_active_unit(db: Session, user_id: int) -> bool:
    """
    True when this account is the assigned lecturer of at least one
    ACTIVE unit.

    `is_active` matters: archiving an admin's last unit must put them
    back on the admin panel, otherwise the sidebar keeps offering a
    dashboard whose every endpoint now returns empty.

    EXISTS-shaped rather than a count - the answer is a boolean and a
    lecturer with forty units should not pay for thirty-nine rows to
    learn it.
    """
    return (
        db.execute(
            select(Unit.id)
            .where(Unit.lecturer_id == user_id, Unit.is_active.is_(True))
            .limit(1)
        ).first()
        is not None
    )


def uses_lecturer_surface(db: Session, user: User) -> bool:
    """
    The single predicate the API and the browser both answer with.

    A LECTURER always qualifies, units or none: an account created five
    minutes ago has no units yet, and the dashboard's documented empty
    state is the correct thing to show them, not the admin panel they
    have no permission for.

    An ADMIN qualifies only while holding a unit.
    """
    if user.role == UserRole.LECTURER:
        return True
    if user.role == UserRole.ADMIN:
        return holds_active_unit(db, user.id)
    return False