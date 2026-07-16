"""
Criteria model — a lecturer-defined assessable component for a Unit (e.g. "Quiz 1", "Attendance"), with a weight and risk threshold.

category identifies what this Criteria structurally IS (Attendance, Weekly Tut, Assessment, or Moodle) - separate from `name`, which stays
free text for display purposes. sequence_number only applies to ASSESSMENT (which slot: 1-4) - null for the other 3 categories, since
those are singular per unit.

max_score defines the maximum possible value for this criterion (e.g. 20 for a quiz out of 20, 100 for attendance as a percentage).
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.enums import CriteriaCategory


class Criteria(Base):
    __tablename__ = "criteria"

    id = Column(Integer, primary_key=True, index=True)

    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)

    name = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False, default=100.0)

    # Nullable for now - your 2 existing test rows predate this concept.
    # New Criteria should always set this going forward.
    category = Column(
        Enum(
            CriteriaCategory,
            name="criteriacategory",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    sequence_number = Column(Integer, nullable=True)  # only meaningful for ASSESSMENT

    enabled = Column(Boolean, default=True)

    unit = relationship("Unit", back_populates="criteria")