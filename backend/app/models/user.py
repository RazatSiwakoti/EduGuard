"""
User model — represents any authenticated account in the system:
Super Admin, Admin, or Lecturer.

`role` has no default on purpose: every account must have its role
set explicitly at creation. A missing default means a bug that
forgets to pass `role` fails loudly (IntegrityError) instead of
silently creating a Lecturer - fail closed, not fail open.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)

    # Authentication
    hashed_password = Column(String, nullable=False)

    # Authorization
    # No default: every insert must explicitly state a role, or the
    # database rejects it instead of silently picking one.
    role = Column(
        Enum(
            UserRole,
            name="userrole",
            # Without this, SQLAlchemy persists the enum MEMBER NAME
            # (e.g. "SUPER_ADMIN"), not its value. This forces it to store the lowercase value instead ("super_admin"),
            # matching what the migration below creates in Postgres.
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    is_active = Column(Boolean, default=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login = Column(DateTime(timezone=True), nullable=True)

    # relationships
    units = relationship("Unit", back_populates="lecturer")
    rule_versions = relationship("RuleVersion", back_populates="creator")