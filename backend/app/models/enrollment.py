from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)

    enrollment_date = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="enrollments")
    unit = relationship("Unit", back_populates="enrollments")