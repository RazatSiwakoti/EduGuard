"""
Criteria-domain service functions: the delete-vs-disable decision.

Mirrors unit_service.py's delete_or_archive_unit pattern - never calls
db.commit() or db.rollback(), the calling route owns the transaction.
"""

from sqlalchemy.orm import Session

from app.models.criteria import Criteria
from app.models.assessment_event import AssessmentEvent


def delete_or_disable_criteria(db: Session, criteria: Criteria) -> str:
    """
    Returns "deleted" or "disabled". A Criteria with AssessmentEvent
    history attached can't be hard-deleted - that would either violate
    the FK constraint or silently orphan real ingested data. Instead it
    gets disabled (enabled = False), reusing the flag that already
    exists rather than inventing a second "is_archived" concept.
    """
    has_events = (
        db.query(AssessmentEvent).filter(AssessmentEvent.criteria_id == criteria.id).first()
        is not None
    )

    if has_events:
        criteria.enabled = False
        return "disabled"

    db.delete(criteria)
    return "deleted"