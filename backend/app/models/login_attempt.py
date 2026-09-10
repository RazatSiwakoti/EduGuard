"""Authentication attempt history used for abuse throttling."""

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.sql import func

from app.models.base import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    ip = Column(String, nullable=True)
    succeeded = Column(Boolean, nullable=False, default=False)
    attempted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_login_attempts_email_attempted_at", "email", "attempted_at"),
        Index("ix_login_attempts_ip_attempted_at", "ip", "attempted_at"),
    )
