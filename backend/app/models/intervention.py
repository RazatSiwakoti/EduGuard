"""Append-only records of deliberate lecturer contacts with a student."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="CASCADE"), nullable=False, index=True)
    lecturer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    kind = Column(String, nullable=False, index=True)
    occurred_at = Column(DateTime, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    outcome = Column(String, nullable=True, index=True)
    follow_up_on = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    student = relationship("Student")
    unit = relationship("Unit")
    lecturer = relationship("User")
