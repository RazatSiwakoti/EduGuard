"""
Student model — represents a real student record, shared globally across
all units (a student enrolled in multiple units has exactly one row here).

student_number is the stable, unique real-world identifier (e.g.
university student ID) used to match rows during CSV/manual ingestion.
name and email are NOT reliable match keys — names can collide, emails
can be null or change — so student_number is required and unique from
the start.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    # The real-world identifier lecturers will type/upload (e.g. university
    # student ID). This is what ingestion matches against - not name or email.
    student_number = Column(String, unique=True, nullable=False, index=True)

    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    program = Column(String, nullable=True)

    enrollments = relationship("Enrollment", back_populates="student")
    assessment_events = relationship("AssessmentEvent", back_populates="student")
    risk_scores = relationship("RiskScore", back_populates="student")