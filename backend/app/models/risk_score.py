from sqlalchemy import Column, Integer, Float, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)

    source = Column(String, nullable=False)

    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)

    is_incomplete = Column(Boolean, nullable=False, default=False)
    missing_criteria = Column(String, nullable=True)

    # Human-readable explanation of THIS engine's own decision - rule
    # engine populates from its per-criterion badness breakdown, ML
    # engine populates from SHAP's top contributing features.
    explanation = Column(Text, nullable=True)

    checkpoint_week = Column(Integer, nullable=False, default=8)

    computed_at = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="risk_scores")
    unit = relationship("Unit", back_populates="risk_scores")