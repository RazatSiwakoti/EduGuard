"""
Criteria-domain service functions: the delete-vs-disable decision.

Mirrors unit_service.py's delete_or_archive_unit pattern - never calls
db.commit() or db.rollback(), the calling route owns the transaction.
"""

from sqlalchemy.orm import Session

from app.models.criteria import Criteria
from app.models.assessment_event import AssessmentEvent
from app.services.rule_engine import FIXED_THRESHOLDS, validate_lecturer_threshold


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


# ---------------------------------------------------------------------
# What a lecturer is allowed to write (section D1)
# ---------------------------------------------------------------------

def assert_lecturer_may_create(payload: dict) -> None:
    """
    Guards Criteria creation. Raises ValueError with a readable message.

    Attendance and Moodle are refused outright rather than floor-checked:
    `seed_default_criteria` already created exactly one of each when the
    unit was created, and a second one would not "override" the first -
    the rule engine would blend BOTH, silently double-counting the
    strongest signal in the system.
    """
    category = payload.get("category")
    key = getattr(category, "value", category)

    if key in FIXED_THRESHOLDS:
        raise ValueError(
            f"{str(key).replace('_', ' ').title()} is created automatically with "
            "every unit and cannot be added again."
        )

    threshold = payload.get("threshold")
    if threshold is not None:
        validate_lecturer_threshold(category, threshold)


def assert_lecturer_may_update(criteria: Criteria, changes: dict) -> None:
    """
    Guards a Criteria PATCH. Raises ValueError with a readable message.

    TWO SEPARATE RULES, AND THE ORDER MATTERS.

    Attendance and Moodle are structurally fixed: their weight, threshold
    and max_score come from `risk_constants` and the rule engine was
    tuned around them. Refusing the whole write is deliberate - silently
    dropping a field the caller believes it changed is worse than an
    error, and it is how a lecturer ends up convinced they lowered a bar
    that never moved.

    A no-op write is allowed through. A PATCH that merely echoes the
    current value has changed nothing, and rejecting it would break any
    client that sends the whole object back.
    """
    key = getattr(criteria.category, "value", criteria.category)

    if key in FIXED_THRESHOLDS:
        # Compare against what is already stored: only an actual change
        # is refused.
        for field in ("threshold", "weight", "max_score", "category", "enabled"):
            if field in changes and changes[field] != getattr(criteria, field):
                raise ValueError(
                    f"{str(key).replace('_', ' ').title()} is fixed for every unit "
                    f"and its {field.replace('_', ' ')} cannot be changed."
                )
        return

    # The category can be changed, so the floor must be checked against
    # the category the row will HAVE after the write, not the one it has
    # now - otherwise relabelling a criterion sidesteps its floor.
    target_category = changes.get("category", criteria.category)
    if "threshold" in changes:
        validate_lecturer_threshold(target_category, changes["threshold"])
    elif "category" in changes:
        validate_lecturer_threshold(target_category, criteria.threshold)