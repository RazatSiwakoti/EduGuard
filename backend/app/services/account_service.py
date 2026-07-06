"""
User-domain service functions: the account lifecycle for Admins and
Lecturers. Deliberately does not know anything about Unit-specific
business rules (e.g. the archive-vs-delete data guard) - it only ever
touches User rows and the two foreign keys that point at them
(Unit.lecturer_id, RuleVersion.created_by), delegating any Unit-specific
logic to unit_service. Kept domain-focused on purpose - this file should
never grow Unit-specific rules of its own.

Never calls db.commit() or db.rollback() - the calling route owns the
transaction boundary.
"""

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.rule_version import RuleVersion
from app.core.system_accounts import get_or_create_placeholder_user
from app.services import unit_service


def delete_user_with_cleanup(db: Session, user: User) -> None:
    """
    Deletes a Lecturer or Admin account safely:
    - any Units they own are unassigned (delegated to unit_service, so
      lecturer_id and status stay in sync the same way they do everywhere
      else)
    - any RuleVersions they authored are reassigned to the permanent
      placeholder account, preserving the NOT NULL foreign key
    - the User row is deleted last, once nothing still points to it
    """
    for unit in list(user.units):
        unit_service.unassign_lecturer(db, unit)

    placeholder = get_or_create_placeholder_user(db)
    db.query(RuleVersion).filter(RuleVersion.created_by == user.id).update(
        {"created_by": placeholder.id}
    )

    db.delete(user)