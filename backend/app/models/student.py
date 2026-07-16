"""
Student model — represents a real student record, shared globally across
all units (a student enrolled in multiple units has exactly one row here).

student_number is the stable, unique real-world identifier (e.g.
university student ID) used to match rows during CSV/manual ingestion.

gender, age are new — passive demographic features for the ML model.
Nullable since existing students don't have this data yet, and a
lecturer's upload may not always include it.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    student_number = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    program = Column(String, nullable=True)

    gender = Column(String, nullable=True)  # "M" / "F"
    age = Column(Integer, nullable=True)

    enrollments = relationship("Enrollment", back_populates="student")
    assessment_events = relationship("AssessmentEvent", back_populates="student")
    risk_scores = relationship("RiskScore", back_populates="student")