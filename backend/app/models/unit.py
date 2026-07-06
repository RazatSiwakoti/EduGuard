"""
Unit model — represents an academic subject (e.g. ICT729).
Owned by a lecturer (User) via lecturer_id.

start_date added to support Week 8 checkpoint calculations later —
needed to determine which academic week a given AssessmentEvent.date
falls into. Nullable for now so existing units without a set date
don't break.

"""

from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey
from sqlalchemy.sql import true
from sqlalchemy.orm import relationship
from app.models.base import Base


class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    unit_code = Column(String, unique=True, nullable=False)
    unit_name = Column(String, nullable=False)

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