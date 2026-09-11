from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)

    enrollment_date = Column(DateTime, server_default=func.now())

    # Ground truth is recorded at enrolment grain: the same student can
    # pass one unit and fail another.  NULL means the unit is unresolved.
    final_outcome = Column(String, nullable=True, index=True)
    final_mark = Column(Float, nullable=True)
    outcome_recorded_at = Column(DateTime, nullable=True)
    outcome_recorded_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    student = relationship("Student", back_populates="enrollments")
    unit = relationship("Unit", back_populates="enrollments")
    outcome_recorder = relationship("User", foreign_keys=[outcome_recorded_by])