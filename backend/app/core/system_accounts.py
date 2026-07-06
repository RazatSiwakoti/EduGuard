"""
System-level placeholder accounts.

get_or_create_placeholder_user() returns a permanent, unusable User row that RuleVersion.created_by gets reassigned to when its real author is
deleted - keeps the NOT NULL foreign key intact without preserving a login-capable account for someone who no longer works here.

Deliberately
- role=LECTURER (lowest privilege of the three, in case any future bug  ever skipped the is_active check on this account)
- is_active=False permanently - it can never log in
- a hashed_password that isn't a valid bcrypt hash of anything - even if someone had it, it can't verify against any password
- excluded from all Admin/Lecturer listings by its reserved email
"""

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.enums import UserRole

PLACEHOLDER_USER_EMAIL = "system.deleted-user@eduguard.internal"


def get_or_create_placeholder_user(db: Session) -> User:
    """Idempotent - returns the same row every time, creating it on first use."""
    placeholder = db.query(User).filter(User.email == PLACEHOLDER_USER_EMAIL).first()
    if placeholder:
        return placeholder

    placeholder = User(
        email=PLACEHOLDER_USER_EMAIL,
        full_name="Deleted User",
        # Not a real bcrypt hash - structurally can never match any password
        # a real login attempt would supply.
        hashed_password="!disabled!",
        role=UserRole.LECTURER,
        is_active=False,
    )
    db.add(placeholder)
    db.commit()
    db.refresh(placeholder)
    return placeholder