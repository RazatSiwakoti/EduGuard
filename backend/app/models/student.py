from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    program = Column(String, nullable=True)

    enrollments = relationship("Enrollment", back_populates="student")
    assessment_events = relationship("AssessmentEvent", back_populates="student")
    risk_scores = relationship("RiskScore", back_populates="student")