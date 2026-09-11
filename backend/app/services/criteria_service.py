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


# ---------------------------------------------------------------------
# What a lecturer may write through the PER-ITEM endpoint (section T4)
# ---------------------------------------------------------------------

#: The only field a lecturer may PATCH on a criterion.
#:
#: Before T2 this endpoint was the only way a unit got configured, so it
#: accepted everything. T2 moved the SHAPE - name, kind, percentage, and
#: the weight and max_score derived from it - to the coordinator's
#: admin PUT, which is the only place the composition rules (max 3
#: items, 20% quiz cap, 100% budget) are checked. Leaving the per-item
#: PATCH wide open left a back door straight past all of them: a
#: lecturer could re-weight an assessment to 90%, or flip its category,
#: and no composition rule would ever see it.
#:
#: `threshold` stays because it is the lecturer's own decision - where
#: the pass bar sits (section T4's slider). Everything else is the
#: coordinator's.
LECTURER_EDITABLE_FIELDS = frozenset({"threshold"})


def assert_lecturer_edits_only_threshold(changes: dict) -> None:
    """
    Raises ValueError naming every field a lecturer may not set.

    REFUSED, NOT FILTERED. Quietly dropping the fields and applying the
    rest is worse: the client gets a 200 and a response body that
    disagrees with what it sent, and a lecturer walks away believing
    they changed a weight that never moved. Same reasoning as D1's
    fixed-category guard, one field-set out.

    Checked BEFORE the shape lock, and the order is the honest one. "You
    may never set this field" is permanent; "not right now" is timing.
    Reporting a locked unit first would tell a lecturer that an
    administrator could unlock the unit and let them change a weight -
    which is not true, and never will be.
    """
    forbidden = sorted(set(changes) - LECTURER_EDITABLE_FIELDS)
    if not forbidden:
        return

    names = [field.replace("_", " ") for field in forbidden]
    listed = names[0] if len(names) == 1 else (
        ", ".join(names[:-1]) + " and " + names[-1]
    )
    raise ValueError(
        "A lecturer can only change a criterion's pass threshold - "
        f"{listed} {'are' if len(names) > 1 else 'is'} set by the unit "
        "coordinator on the unit's criteria setup screen."
    )