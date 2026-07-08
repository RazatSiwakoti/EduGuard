"""
IngestionBatch model — records one bulk upload event: which unit,
which lecturer, which file, and how many individual score values
succeeded/failed.

values_stored / values_failed count individual criteria-values across
all rows, NOT rows themselves - a single row with 3 criteria columns
can contribute up to 3 values. total_rows is the only row-level count
here; "how many rows had at least one error" is derived at the API
response layer from the error list, not stored separately.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id = Column(Integer, primary_key=True, index=True)

    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    lecturer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now())

    total_rows = Column(Integer, nullable=False, default=0)
    values_stored = Column(Integer, nullable=False, default=0)
    values_failed = Column(Integer, nullable=False, default=0)

    unit = relationship("Unit", back_populates="ingestion_batches")
    assessment_events = relationship("AssessmentEvent", back_populates="batch")