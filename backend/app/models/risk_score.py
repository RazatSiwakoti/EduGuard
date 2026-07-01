from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)

    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)

    computed_at = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="risk_scores")
    unit = relationship("Unit", back_populates="risk_scores")