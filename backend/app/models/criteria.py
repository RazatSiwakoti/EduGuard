"""
Criteria model — a lecturer-defined assessable component for a Unit
(e.g. "Quiz 1", "Attendance"), with a weight and risk threshold.

max_score defines the maximum possible value for this criterion (e.g.
20 for a quiz out of 20, 100 for attendance as a percentage). This is
required for ingestion to validate incoming scores are actually in range
(a score can never exceed what the criterion is out of) - threshold is
a risk cutoff for later analysis, not a validation bound, so it can't
serve this purpose on its own.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Criteria(Base):
    __tablename__ = "criteria"

    id = Column(Integer, primary_key=True, index=True)

    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)

    name = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)

    # Maximum possible value for this criterion - required so ingestion
    # can reject an out-of-range score (e.g. attendance > 100%).
    max_score = Column(Float, nullable=False, default=100.0)

    enabled = Column(Boolean, default=True)

    unit = relationship("Unit", back_populates="criteria")