"""Shared longitudinal checkpoint definitions and database helpers."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.final_verdicts import FinalVerdict

CHECKPOINT_WEEKS = (4, 8, 12)
DEFAULT_CHECKPOINT_WEEK = 8


def resolve_checkpoint(requested: Optional[int]) -> int:
    """Return a valid requested checkpoint, or the current default."""
    return requested if requested in CHECKPOINT_WEEKS else DEFAULT_CHECKPOINT_WEEK


def available_checkpoints(
    db: Session, unit_id: Optional[int] = None
) -> list[int]:
    """Return checkpoint weeks for which verdicts exist."""
    stmt = select(FinalVerdict.checkpoint_week).distinct()
    if unit_id is not None:
        stmt = stmt.where(FinalVerdict.unit_id == unit_id)
    return sorted(db.execute(stmt).scalars().all())
