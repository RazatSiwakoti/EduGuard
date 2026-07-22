"""
Unit model — represents one specific teaching offering of an academic
subject (e.g. ICT729, Year 2026, Semester 1).

start_date supports Week 8 checkpoint calculations later —
needed to determine which academic week a given AssessmentEvent.date
falls into.

year + teaching_period identify WHICH offering this is. unit_code alone
is no longer unique, since the same subject is taught every semester —
uniqueness is now enforced on the (unit_code, year, teaching_period)
combination instead.

level ("bachelor"/"master") is informational only, not enforced at the
database level - real enrolment can have messy edge cases (bridging
students, dual-pathway students) that a hard constraint would wrongly
block. Useful for reporting and the ML pipeline, not a hard rule.
"""

from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.sql import true
from sqlalchemy.orm import relationship
from app.models.base import Base


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint(
            "unit_code", "year", "teaching_period",
            name="uq_unit_code_year_period",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    unit_code = Column(String, nullable=False)
    unit_name = Column(String, nullable=False)

    year = Column(Integer, nullable=True)
    teaching_period = Column(String, nullable=True)

    # Informational only - see docstring above. Plain string, not an
    # Enum, since it's not enforced and keeping it simple avoids a
    # migration later if a third level (e.g. "diploma") ever appears.
    level = Column(String, nullable=True)

    start_date = Column(Date, nullable=True)

    lecturer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    status = Column(String, nullable=False, default="UNASSIGNED")

    lecturer = relationship("User", back_populates="units")
    enrollments = relationship("Enrollment", back_populates="unit")
    criteria = relationship("Criteria", back_populates="unit")
    rule_versions = relationship("RuleVersion", back_populates="unit")
    assessment_events = relationship("AssessmentEvent", back_populates="unit")
    risk_scores = relationship("RiskScore", back_populates="unit")
    ingestion_batches = relationship("IngestionBatch", back_populates="unit")