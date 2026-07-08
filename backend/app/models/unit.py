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
    unit_code = Column(String, nullable=False)  # no longer unique alone
    unit_name = Column(String, nullable=False)

    # Identifies which offering this Unit row represents.
    # Nullable for now: existing rows predate this concept and have no
    # known value. New units should always set both going forward —
    # enforced at the service/API layer, not the DB, to avoid breaking
    # existing data on migration.
    year = Column(Integer, nullable=True)
    teaching_period = Column(String, nullable=True)  # e.g. "S1", "S2", "Summer"

    # Semester/teaching period start — used later to calculate
    # "Week N" from AssessmentEvent.date (e.g. Week 8 checkpoint)
    start_date = Column(Date, nullable=True)

    # Nullable: a unit can exist with no lecturer assigned yet, or be
    # left unassigned after its lecturer's account is deleted.
    lecturer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Archive flag — set to False instead of deleting when the unit has
    # real academic data attached. NOT NULL on purpose: "is this unit
    # active" should never be allowed to sit ambiguous.
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    status = Column(String, nullable=False, default="UNASSIGNED")

    lecturer = relationship("User", back_populates="units")
    enrollments = relationship("Enrollment", back_populates="unit")
    criteria = relationship("Criteria", back_populates="unit")
    rule_versions = relationship("RuleVersion", back_populates="unit")
    assessment_events = relationship("AssessmentEvent", back_populates="unit")
    risk_scores = relationship("RiskScore", back_populates="unit")
    ingestion_batches = relationship("IngestionBatch", back_populates="unit")