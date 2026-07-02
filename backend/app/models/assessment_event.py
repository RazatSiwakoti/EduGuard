from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class AssessmentEvent(Base):
    __tablename__ = "assessment_events"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)

    event_type = Column(String, nullable=False)
    score = Column(Float, nullable=False)

    date = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="assessment_events")
    unit = relationship("Unit", back_populates="assessment_events")