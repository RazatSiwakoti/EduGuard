"""
AssessmentEvent model — one raw, immutable data point: a student's score
against a specific Criteria in a specific Unit.

Immutable by design (see #3 in Phase 4 planning: never modify raw data).
Ingestion only ever INSERTs here - a correction is a new row, never an
UPDATE to an old one. "Current value" for a given (student, unit,
criteria) is derived by querying the latest row by `date`, not stored
as a separate flag.

criteria_id replaces the old free-text event_type column - event_type
duplicated what Criteria.name already stores (a single-source-of-truth
violation), and gave ingestion no way to validate against max_score or
look up weight/threshold for later risk calculation.

batch_id is nullable: bulk-uploaded rows point to the IngestionBatch
they came from; manually entered single rows have no batch and stay
NULL - there's no file to group them under.
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base
from app.models.enums import EventSource


class AssessmentEvent(Base):
    __tablename__ = "assessment_events"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    criteria_id = Column(Integer, ForeignKey("criteria.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("ingestion_batches.id"), nullable=True)

    score = Column(Float, nullable=False)

    source = Column(
        Enum(
            EventSource,
            name="eventsource",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    # Which lecturer submitted this event - audit trail (#3, #11).
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    date = Column(DateTime, server_default=func.now())

    student = relationship("Student", back_populates="assessment_events")
    unit = relationship("Unit", back_populates="assessment_events")
    criteria = relationship("Criteria")
    creator = relationship("User")
    batch = relationship("IngestionBatch", back_populates="assessment_events")