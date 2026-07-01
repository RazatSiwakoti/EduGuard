from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    unit_code = Column(String, unique=True, nullable=False)
    unit_name = Column(String, nullable=False)

    lecturer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    lecturer = relationship("User", back_populates="units")
    enrollments = relationship("Enrollment", back_populates="unit")
    criteria = relationship("Criteria", back_populates="unit")
    rule_versions = relationship("RuleVersion", back_populates="unit")
    assessment_events = relationship("AssessmentEvent", back_populates="unit")
    risk_scores = relationship("RiskScore", back_populates="unit")