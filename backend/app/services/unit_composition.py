"""
The two lives of a unit's shape (section T1).

A unit is configured once and then used. Those are two different modes,
and almost every rule in this block exists because they were previously
the same mode:

  DRAFT   - nobody has recorded a mark against this unit's assessments
            and no analysis has run. The coordinator may add, remove and
            re-weight criteria freely.

  LOCKED  - real assessment or tutorial results exist, or a risk analysis
            has produced verdicts. The shape is now load-bearing: every
            score in the database was computed against it, and
            `weight = pct / 100` means changing a mark total silently
            re-weights the risk blend for every student in the unit.

WHAT DOES *NOT* LOCK A UNIT, AND WHY IT MATTERS MOST
----------------------------------------------------
Attendance and Moodle events are `AssessmentEvent` rows exactly like a
quiz mark, so the obvious rule - "any ingested data locks the shape" -
would freeze a unit the moment a lecturer uploaded week-1 attendance,
which happens *before* the coordinator has entered a single assessment.
The unit would arrive at configuration time already locked, and the only
way through would be the admin unlock path, on every unit, every
semester. That is not a safety rail; it is a permanently jammed door.

So the lock is keyed on the two categories that carry the coordinator's
decisions - `assessment` and `weekly_tut` - plus the existence of any
`FinalVerdict`. Attendance and Moodle are seeded automatically, sit
outside the 100% mark budget and are not editable anyway (section D1),
so nothing about them can be invalidated by a shape change.

A RENAME IS NEVER A SHAPE CHANGE
--------------------------------
`name` is free text for display. Renaming "Quiz 1" to "Week 4 Quiz"
invalidates nothing, so it is allowed in either life, and - equally
important - it does not mark analyses stale and does not consume the
one-shot unlock window. A coordinator who unlocks a unit, fixes a typo
in a label and finds the door has closed behind them would rightly
conclude the feature is broken.

STALENESS IS DERIVED, NEVER STORED
----------------------------------
There is no `is_stale` flag. A verdict is stale when it was computed
before the last shape change - `FinalVerdict.created_at <
Unit.criteria_updated_at` - and that comparison is made at read time.
A stored flag would need updating on every write path that could
possibly change a shape, and the one that got missed would be the one
that mattered.

TRANSACTION OWNERSHIP
---------------------
Mirrors `criteria_service` and `unit_service`: nothing here calls
`db.commit()` or `db.rollback()`. The calling route owns the
transaction, so a lock refusal cannot half-apply a write.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assessment_event import AssessmentEvent
from app.models.criteria import Criteria
from app.models.enums import AssessmentKind, CriteriaCategory
from app.models.final_verdicts import FinalVerdict
from app.models.unit import Unit

# ---------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------

DRAFT = "draft"
LOCKED = "locked"

#: The categories whose data represents the coordinator's decisions.
#: Attendance and Moodle are deliberately absent - see the module
#: docstring. Held as enum members, not strings, so a typo is an
#: AttributeError at import time rather than a lock that never engages
#: (which is exactly how D1's `floors` dict stayed broken for months).
LOCKING_CATEGORIES = (CriteriaCategory.ASSESSMENT, CriteriaCategory.WEEKLY_TUT)

#: Fields on a Criteria row that describe a label rather than a rule.
#: Changing only these is permitted while locked.
LABEL_ONLY_FIELDS = frozenset({"name"})

#: Fields whose change genuinely re-shapes the unit. Anything not listed
#: in LABEL_ONLY_FIELDS is treated as a shape change, so a column added
#: later defaults to "safe" rather than silently escaping the lock.


class ShapeLockedError(Exception):
    """
    Raised when a write is refused because the unit's shape is locked.

    Deliberately NOT a ValueError. D1's guards raise ValueError for "that
    number is not allowed", which the route renders as 400. A lock is a
    different kind of refusal: the payload is fine and would have been
    accepted yesterday. The route renders this as 409 Conflict so the UI
    can tell the two apart and offer the unlock path for one of them and
    a corrected number for the other.
    """

    def __init__(self, message: str, reasons: Optional[list[str]] = None):
        super().__init__(message)
        self.reasons = reasons or []


# ---------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: Optional[datetime]) -> Optional[datetime]:
    """
    PostgreSQL columns in this project are naive; comparisons need a
    timezone. Same helper as `report_service._as_aware` - duplicated
    rather than imported because a service module importing a reporting
    module for a two-line date helper is the wrong dependency direction.
    """
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------
# Counting what locks a unit
# ---------------------------------------------------------------------

def locking_event_count(db: Session, unit_id: int) -> int:
    """
    How many AssessmentEvent rows sit on an assessment or weekly-tutorial
    criterion for this unit.

    Joined through Criteria rather than filtered on AssessmentEvent
    alone, because the category lives on the criterion. Both sides are
    constrained to the unit: `AssessmentEvent.unit_id` is denormalised
    and a mismatched row would otherwise be counted for two units.
    """
    return int(
        db.execute(
            select(func.count(AssessmentEvent.id))
            .join(Criteria, Criteria.id == AssessmentEvent.criteria_id)
            .where(
                AssessmentEvent.unit_id == unit_id,
                Criteria.unit_id == unit_id,
                Criteria.category.in_(LOCKING_CATEGORIES),
            )
        ).scalar()
        or 0
    )


def verdict_count(db: Session, unit_id: int) -> int:
    """Every FinalVerdict ever produced for this unit, at any checkpoint."""
    return int(
        db.execute(
            select(func.count(FinalVerdict.id)).where(FinalVerdict.unit_id == unit_id)
        ).scalar()
        or 0
    )


def shape_lock_state(db: Session, unit: Unit) -> dict:
    """
    Whether this unit's shape may currently be edited, and why not.

    Returns a dict rather than a bare enum because every caller needs the
    reason as well as the answer: the API returns it, the form displays
    it, and a refusal message quotes it. Splitting "is it locked" from
    "why is it locked" into two functions guarantees they eventually
    disagree.

    Keys:
      state                 "draft" | "locked" - the EFFECTIVE state,
                            i.e. after an active unlock is applied
      locked                bool, the same thing as `state == "locked"`
      lockable              bool - would it be locked if not unlocked?
      unlock_active         bool - an admin unlock is open right now
      reasons               human-readable list, empty when draft
      locking_event_count   assessment/tutorial results recorded
      verdict_count         analyses produced
    """
    events = locking_event_count(db, unit.id)
    verdicts = verdict_count(db, unit.id)

    reasons: list[str] = []
    if events:
        reasons.append(
            f"{events} assessment or tutorial result"
            f"{'s have' if events != 1 else ' has'} been recorded against this "
            "unit's criteria."
        )
    if verdicts:
        reasons.append(
            f"{verdicts} risk analysis result{'s' if verdicts != 1 else ''} "
            f"{'have' if verdicts != 1 else 'has'} been produced from the current "
            "shape."
        )

    lockable = bool(reasons)
    unlock_active = getattr(unit, "criteria_unlocked_at", None) is not None
    locked = lockable and not unlock_active

    return {
        "state": LOCKED if locked else DRAFT,
        "locked": locked,
        "lockable": lockable,
        "unlock_active": unlock_active and lockable,
        "reasons": reasons,
        "locking_event_count": events,
        "verdict_count": verdicts,
        "criteria_updated_at": _as_aware(getattr(unit, "criteria_updated_at", None)),
        "criteria_unlocked_at": _as_aware(getattr(unit, "criteria_unlocked_at", None)),
    }


# ---------------------------------------------------------------------
# What counts as a shape change
# ---------------------------------------------------------------------

def effective_changes(criteria: Criteria, changes: dict) -> dict:
    """
    The subset of a PATCH that actually changes something.

    A client that sends the whole object back has changed nothing, and
    must not be refused for echoing values it never touched. D1 makes the
    same allowance for fixed categories; the lock has to make it too, or
    the two guards disagree about what a "change" is.
    """
    return {
        field: value
        for field, value in changes.items()
        if value != getattr(criteria, field, None)
    }


def is_shape_change(effective: dict) -> bool:
    """
    True when a change touches anything other than a display label.

    Note the direction of the test: anything NOT in LABEL_ONLY_FIELDS is
    a shape change. A column added to Criteria later is therefore locked
    by default rather than quietly exempt.
    """
    return bool(set(effective) - LABEL_ONLY_FIELDS)


# ---------------------------------------------------------------------
# The guards
# ---------------------------------------------------------------------

def _refuse(state: dict, action: str) -> None:
    raise ShapeLockedError(
        f"This unit's criteria are locked and cannot be {action}. "
        + " ".join(state["reasons"])
        + " An administrator can unlock the unit for one edit.",
        reasons=state["reasons"],
    )


def assert_may_create_criteria(db: Session, unit: Unit) -> None:
    """Adding a criterion is always a shape change."""
    state = shape_lock_state(db, unit)
    if state["locked"]:
        _refuse(state, "added to")


def assert_may_delete_criteria(db: Session, unit: Unit) -> None:
    """
    Removing a criterion is always a shape change.

    Worth stating explicitly: `criteria_service.delete_or_disable_criteria`
    DISABLES rather than deletes a criterion that has events attached, and
    a disabled criterion is excluded from the report and from the rule
    engine's blend. Soft-deleting is still deleting as far as every score
    already computed is concerned, so the lock covers it.
    """
    state = shape_lock_state(db, unit)
    if state["locked"]:
        _refuse(state, "removed from")


def assert_may_update_criteria(db: Session, unit: Unit, criteria: Criteria,
                               changes: dict) -> None:
    """
    Guards a Criteria PATCH against the lock. Runs alongside D1's
    threshold rules, not instead of them.

    Three outcomes:
      - nothing actually changed        -> allowed, in either life
      - only the display name changed   -> allowed, in either life
      - anything else                   -> refused while locked
    """
    effective = effective_changes(criteria, changes)
    if not effective:
        return
    if not is_shape_change(effective):
        return

    state = shape_lock_state(db, unit)
    if state["locked"]:
        _refuse(state, "changed")


# ---------------------------------------------------------------------
# Recording a write
# ---------------------------------------------------------------------

def record_criteria_write(unit: Unit, *, shape_changed: bool = True,
                          now: Optional[datetime] = None) -> None:
    """
    Called by the route AFTER a criteria write succeeds and BEFORE the
    commit, so the timestamp and the write land in one transaction.

    `shape_changed=False` is for a rename. A rename must not mark a
    single analysis stale, and must not burn the one-shot unlock window -
    a coordinator who unlocks a unit, fixes a typo and finds the door has
    shut behind them would reasonably conclude the feature is broken.
    """
    if not shape_changed:
        return

    unit.criteria_updated_at = (now or _now()).replace(tzinfo=None)

    # One-shot: the unlock existed to permit exactly this write.
    unit.criteria_unlocked_at = None
    unit.criteria_unlocked_by = None


# ---------------------------------------------------------------------
# Unlocking
# ---------------------------------------------------------------------

def unlock_preview(db: Session, unit: Unit) -> dict:
    """
    What an unlock will cost, computed BEFORE anyone commits to it.

    The number that matters is not how many verdicts exist - it is how
    many are still current and would be invalidated by the edit the
    unlock enables. Verdicts already stale from an earlier shape change
    are counted separately: re-invalidating something already invalid
    costs nothing, and quoting the larger number would overstate the
    damage and scare a coordinator off a legitimate correction.
    """
    state = shape_lock_state(db, unit)
    stale = stale_verdict_summary(db, unit)

    current = state["verdict_count"] - stale["stale_count"]
    students = int(
        db.execute(
            select(func.count(func.distinct(FinalVerdict.student_id)))
            .where(FinalVerdict.unit_id == unit.id)
        ).scalar()
        or 0
    )

    return {
        **state,
        "unit_code": unit.unit_code,
        "verdicts_currently_valid": max(current, 0),
        "verdicts_already_stale": stale["stale_count"],
        "students_affected": students,
        # Stated as a consequence of SAVING, not of unlocking. Unlocking
        # by itself changes no numbers; see `unlock_shape`.
        "consequence": (
            f"Saving a change will mark {max(current, 0)} risk "
            f"result{'s' if max(current, 0) != 1 else ''} across {students} "
            f"student{'s' if students != 1 else ''} as computed against an "
            "older unit shape. The unit must be re-analysed for those results "
            "to mean anything again."
        ),
    }


def unlock_shape(db: Session, unit: Unit, confirmation: str,
                 actor_id: Optional[int] = None,
                 now: Optional[datetime] = None) -> dict:
    """
    Opens a one-shot edit window. Raises ValueError if the typed
    confirmation does not match the unit code.

    Case-insensitive and whitespace-trimmed: the confirmation exists to
    prove the admin knows WHICH unit they are unlocking, and rejecting
    "ict729" for "ICT729" tests their shift key, not their intent.

    IT DOES NOT MARK ANYTHING STALE. `criteria_updated_at` is untouched
    here on purpose - an admin who unlocks a unit, looks at the form and
    closes it has changed nothing, and should not have invalidated a
    single result. The staleness lands on the save, which is where the
    shape actually changes. (The one-line summary in D-RUNBOOK's decision
    table reads "unlock ... marks analyses stale"; the T1 build spec in
    the same document says unlock sets a flag and every write bumps the
    timestamp. This implements the build spec - see the guide.)

    Unlocking an already-unlocked unit is idempotent, not an error: two
    admins clicking the same button should not produce a failure.
    """
    typed = (confirmation or "").strip().casefold()
    expected = (unit.unit_code or "").strip().casefold()
    if not expected or typed != expected:
        raise ValueError(
            f"Type the unit code exactly to confirm. Expected {unit.unit_code}."
        )

    state = shape_lock_state(db, unit)
    if not state["lockable"]:
        # Nothing to unlock. Returning the state rather than raising:
        # the caller asked for an editable unit and has one.
        return {**state, "unlocked": False,
                "detail": "This unit is already in draft - no unlock was needed."}

    unit.criteria_unlocked_at = (now or _now()).replace(tzinfo=None)
    unit.criteria_unlocked_by = actor_id

    return {
        **shape_lock_state(db, unit),
        "unlocked": True,
        "detail": (
            "Unlocked for one edit. The lock returns as soon as a change is "
            "saved. No results have been marked stale yet - that happens on "
            "save."
        ),
    }


# ---------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------

def stale_verdict_summary(db: Session, unit: Unit,
                          checkpoint_week: Optional[int] = None) -> dict:
    """
    Verdicts computed against a shape that no longer exists.

    Derived, never stored. `criteria_updated_at` is NULL for every unit
    that existed before this migration, which correctly means "no shape
    change has been recorded, so nothing is stale" - back-filling it with
    the migration date would have declared every historical result
    suspect on the day the feature shipped.
    """
    changed_at = _as_aware(getattr(unit, "criteria_updated_at", None))
    empty = {
        "stale_count": 0,
        "student_count": 0,
        "changed_at": changed_at,
        "total_count": 0,
    }
    if changed_at is None:
        return empty

    query = select(FinalVerdict).where(FinalVerdict.unit_id == unit.id)
    if checkpoint_week is not None:
        query = query.where(FinalVerdict.checkpoint_week == checkpoint_week)

    verdicts = list(db.execute(query).scalars())
    stale = [
        verdict
        for verdict in verdicts
        # Compared in Python, not SQL: `created_at` is naive on
        # PostgreSQL and `changed_at` is aware, and letting the database
        # compare them is how a silent off-by-a-timezone appears.
        if (_as_aware(verdict.created_at) or changed_at) < changed_at
    ]

    return {
        "stale_count": len(stale),
        "student_count": len({verdict.student_id for verdict in stale}),
        "changed_at": changed_at,
        "total_count": len(verdicts),
    }



# =====================================================================
# SECTION T2 - THE COMPOSITION RULES
# =====================================================================
#
# T1 above decides WHEN a unit's shape may be changed. Everything below
# decides WHAT a legal shape is, and materialises one.
#
# The coordinator answers three questions and nothing else:
#
#   1. Does this unit run weekly tutorials?   yes / no, fixed at 10%
#   2. Which assessments does it have?        up to 3
#   3. What is each one worth?                a percentage of the unit
#
# Attendance and Moodle are not among them. They are seeded at unit
# creation from `risk_constants`, sit OUTSIDE the 100% mark budget, and
# are refused by D1's guards - so the shape API never writes them and
# never deletes them (see `replace_unit_shape`, which is scoped by
# category for exactly this reason).
#
# ---------------------------------------------------------------------
# THE ONE THAT WOULD HAVE BROKEN SCORING SILENTLY
# ---------------------------------------------------------------------
# The runbook states the rule as `max_score = pct` and `weight = pct/100`.
# That is right for an assessment and WRONG for the weekly tutorial, and
# applying it uniformly - the obvious reading - breaks the rule engine
# without raising anything.
#
# An assessment's AssessmentEvent.score is a RAW MARK: a quiz worth 20%
# of the unit is marked out of 20, and 15 is stored as 15.
# `rule_score_service.normalise_to_percentage` divides by `max_score` to
# get 75%. So `max_score = pct` is exactly correct there.
#
# A weekly tutorial's score is NOT a raw mark. It is already a completion
# PERCENTAGE, produced by `rule_engine.calculate_tutorial_completion_pct`
# from the weekly submitted/late/not_submitted statuses, and stored on a
# 0-100 scale. Writing `max_score = 10` for a 10% tutorial would mean:
#
#   * `ingestion_service.validate_score` refuses every completion above
#     10 - "Score 75.0 out of range for 'Weekly Tutorials' (valid range
#     0-10)" - so a normal tutorial import fails as a data error
#   * `rule_score_service.normalise_to_percentage` computes
#     75 / 10 * 100 = 750%, which `calculate_badness` clamps to zero
#     badness: EVERY student passes tutorials, forever
#   * `ml_score_service` divides by the same max_score, so the ML side
#     agrees with the wrong number rather than disagreeing with it -
#     no "requires review" flag would ever surface it
#
# So the tutorial's 10% is carried entirely by `weight = 0.10`, and its
# `max_score` stays 100.0, matching what every other percentage-scaled
# criterion in this system is seeded with.
#
# ---------------------------------------------------------------------
# WEIGHTS DO NOT NEED TO SUM TO 1
# ---------------------------------------------------------------------
# `rule_engine.compute_rule_based_risk` divides by `total_weight_used`,
# so weights are RELATIVE. Attendance (0.5) and Moodle (0.05) plus a full
# 100% of assessments and tutorials totals 1.55, and that is correct and
# intended - it means assessments together carry roughly 65% of the blend
# against attendance's 32%. Rescaling here to force a sum of 1.0 would
# change every score in the system for no reason.

# --- the numbers the coordinator cannot argue with -------------------

#: Maximum assessment items in one unit. Runbook decision, locked.
MAX_ASSESSMENTS = 3

#: A quiz may not be worth more than this share of the unit.
QUIZ_MAX_PERCENTAGE = 20.0

#: Weekly tutorials are a yes/no with a FIXED share - the coordinator
#: chooses whether the unit has them, never what they are worth.
TUTORIAL_PERCENTAGE = 10.0

#: Assessments + tutorials. Attendance and Moodle are outside it.
MAX_TOTAL_PERCENTAGE = 100.0

#: Every criterion whose score is stored as a percentage rather than a
#: raw mark keeps this ceiling. See the long note above - this is the
#: value that stops a 10% tutorial being read as "marked out of 10".
PERCENTAGE_SCALE_MAX_SCORE = 100.0

#: The pass mark a new item starts at, before a lecturer touches the T4
#: threshold bar. Matches D1's default; the floors (45 / 40) are D1's.
DEFAULT_PASS_PERCENTAGE = 50.0

#: The categories the shape API owns. Anything outside this tuple is
#: read-only to it and, critically, is never deleted by a replace.
SHAPE_CATEGORIES = (CriteriaCategory.ASSESSMENT, CriteriaCategory.WEEKLY_TUT)

#: Seeded, automatic, outside the mark budget. Surfaced by the shape read
#: so the form can SAY they are automatic rather than leaving a
#: coordinator to wonder where the other 55% of the blend went.
FIXED_CATEGORIES = (CriteriaCategory.ATTENDANCE, CriteriaCategory.MOODLE)

DEFAULT_TUTORIAL_NAME = "Weekly Tutorials"


class CompositionError(ValueError):
    """
    A shape that breaks the composition rules.

    A ValueError subclass, so the route renders it 400 exactly like D1's
    refusals - "that number is not allowed" is the same KIND of answer
    whether it came from a floor or from the 100% budget. It is
    deliberately NOT a ShapeLockedError: 409 means "not now", 400 means
    "not like that", and the form does different things with each.
    """


# ---------------------------------------------------------------------
# Validating a proposed shape
# ---------------------------------------------------------------------

def _kind_value(kind: Any) -> Optional[str]:
    """Accepts an AssessmentKind, its value, or None. One place, so the
    rules never compare an enum against a string and quietly pass."""
    if kind is None:
        return None
    return getattr(kind, "value", kind)


def validate_composition(assessments: list[dict], tutorials_enabled: bool) -> None:
    """
    Raises CompositionError on the first broken rule, with a message the
    form can print verbatim.

    THE RULES, AND THE TWO THAT ARE ASYMMETRIC:

      * at most 3 assessments
      * each is a quiz or an assignment - no third kind, no blank
      * each percentage is > 0 and <= 100
      * a QUIZ is capped at 20%; an assignment is not
      * assessments + tutorials must not EXCEED 100%
      * ...but may fall SHORT of it, silently

    The last pair is the asymmetry worth stating. Over 100% is refused
    because it is arithmetically impossible - the unit cannot be worth
    more than itself. Under 100% is accepted without so much as a
    warning, because a unit part-way through configuration is under 100%
    by definition, and a coordinator who adds one assessment at a time
    would otherwise be scolded on every save. It is also legitimately
    final: a unit can carry a component this system does not model.
    """
    if len(assessments) > MAX_ASSESSMENTS:
        raise CompositionError(
            f"A unit can have at most {MAX_ASSESSMENTS} assessments. "
            f"{len(assessments)} were submitted."
        )

    valid_kinds = {member.value for member in AssessmentKind}

    for index, item in enumerate(assessments, start=1):
        label = (item.get("name") or "").strip() or f"Assessment {index}"

        if not (item.get("name") or "").strip():
            raise CompositionError(f"Assessment {index} needs a name.")

        kind = _kind_value(item.get("kind"))
        if kind not in valid_kinds:
            raise CompositionError(
                f"'{label}' must be a quiz or an assignment."
            )

        percentage = item.get("percentage")
        if percentage is None:
            raise CompositionError(f"'{label}' needs a percentage.")
        if percentage <= 0:
            raise CompositionError(
                f"'{label}' must be worth more than 0% of the unit."
            )
        if percentage > MAX_TOTAL_PERCENTAGE:
            raise CompositionError(
                f"'{label}' cannot be worth more than "
                f"{MAX_TOTAL_PERCENTAGE:g}% of the unit."
            )
        if kind == AssessmentKind.QUIZ.value and percentage > QUIZ_MAX_PERCENTAGE:
            raise CompositionError(
                f"A quiz cannot be worth more than {QUIZ_MAX_PERCENTAGE:g}% "
                f"of the unit. '{label}' is set to {percentage:g}%. "
                "Change it to an assignment if it is worth more."
            )

    total = composition_total(assessments, tutorials_enabled)
    if total > MAX_TOTAL_PERCENTAGE:
        tutorial_note = (
            f" (including {TUTORIAL_PERCENTAGE:g}% for weekly tutorials)"
            if tutorials_enabled else ""
        )
        raise CompositionError(
            f"The unit adds up to {total:g}%{tutorial_note}, which is more "
            f"than {MAX_TOTAL_PERCENTAGE:g}%. Reduce a percentage or remove "
            "an item."
        )


def composition_total(assessments: list[dict], tutorials_enabled: bool) -> float:
    """
    Assessments plus the fixed tutorial share. Attendance and Moodle are
    excluded on purpose - they are not marks and are not in the budget.

    Rounded to 2dp before it is compared against 100: three items of
    33.33 each sum to 99.99000000000001 in binary floating point, and an
    unrounded comparison is how a shape that is visibly under 100% gets
    refused for being over it.
    """
    total = sum(float(item.get("percentage") or 0.0) for item in assessments)
    if tutorials_enabled:
        total += TUTORIAL_PERCENTAGE
    return round(total, 2)


def pass_mark(criteria: Criteria) -> Optional[float]:
    """
    The mark a student must reach on this criterion, DERIVED and never
    stored.

    `threshold` is a percentage and `max_score` is the scale, so an
    assignment worth 30 marks with a 50% bar has a pass mark of 15.
    Nothing writes this to the database: a stored pass mark would have to
    be recomputed every time a lecturer moved the T4 slider or a
    coordinator changed a mark total, and the write path that got missed
    would be the one that mattered.
    """
    if criteria.max_score is None or criteria.threshold is None:
        return None
    return round(criteria.max_score * criteria.threshold / 100.0, 2)


# ---------------------------------------------------------------------
# Materialising a shape onto Criteria rows
# ---------------------------------------------------------------------

def assessment_row_values(percentage: float) -> dict:
    """
    The stored columns for one assessment item.

    `max_score = percentage` is correct HERE and only here: an
    assessment's score is a raw mark, so a 30% assignment is marked out
    of 30 and `rule_score_service` divides by 30 to get a percentage.
    """
    return {
        "max_score": float(percentage),
        "weight": round(float(percentage) / 100.0, 4),
    }


def tutorial_row_values() -> dict:
    """
    The stored columns for the weekly-tutorial criterion.

    `max_score` is 100, NOT 10. Read the long note at the top of this
    section before changing it - a tutorial's stored score is already a
    completion percentage, and a max_score of 10 makes every student pass
    tutorials forever without raising anything.
    """
    return {
        "max_score": PERCENTAGE_SCALE_MAX_SCORE,
        "weight": round(TUTORIAL_PERCENTAGE / 100.0, 4),
    }


# ---------------------------------------------------------------------
# Reading a unit's shape
# ---------------------------------------------------------------------

def _shape_criteria(db: Session, unit_id: int, categories) -> list[Criteria]:
    """
    ENABLED criteria in the given categories, ordered so the form always
    renders the same rows in the same order.

    `enabled == False` rows are excluded everywhere in this section. They
    are soft-deleted assessments that still carry AssessmentEvent history
    (see `criteria_service.delete_or_disable_criteria`), and re-surfacing
    one in the form would let a coordinator "re-add" a slot and get last
    semester's marks back with it.
    """
    return (
        db.query(Criteria)
        .filter(
            Criteria.unit_id == unit_id,
            Criteria.category.in_(categories),
            Criteria.enabled.is_(True),
        )
        .order_by(Criteria.sequence_number.is_(None), Criteria.sequence_number,
                  Criteria.id)
        .all()
    )


def _criterion_out(criteria: Criteria, percentage: Optional[float] = None) -> dict:
    """One row as the form and the lecturer's read-only view need it."""
    return {
        "id": criteria.id,
        "name": criteria.name,
        "kind": _kind_value(criteria.kind),
        "category": _kind_value(criteria.category),
        "sequence_number": criteria.sequence_number,
        "percentage": percentage,
        "max_score": criteria.max_score,
        "weight": criteria.weight,
        "threshold": criteria.threshold,
        "pass_mark": pass_mark(criteria),
        "enabled": bool(criteria.enabled),
    }


def get_unit_shape(db: Session, unit: Unit) -> dict:
    """
    Everything the setup form (T3) and the lecturer's read-only view (T4)
    need, in one request.

    `percentage` is reconstructed from `weight`, not from `max_score`,
    and the two are NOT interchangeable. `weight` is the one field that
    means "share of the unit" for both categories; `max_score` means
    "share of the unit" only for assessments, and means "the 0-100 scale"
    for the tutorial. Reading the percentage off `max_score` would report
    a 10% tutorial as being worth 100% of the unit.

    `configured` is what T3's "not configured" badge reads. A unit is
    configured once it has at least one assessment or a tutorial - the
    two seeded rows do not count, because every unit has them from the
    moment it is created and a badge that is never shown is not a badge.
    """
    assessments = _shape_criteria(db, unit.id, (CriteriaCategory.ASSESSMENT,))
    tutorials = _shape_criteria(db, unit.id, (CriteriaCategory.WEEKLY_TUT,))
    fixed = _shape_criteria(db, unit.id, FIXED_CATEGORIES)

    assessment_rows = [
        _criterion_out(row, percentage=round((row.weight or 0.0) * 100.0, 2))
        for row in assessments
    ]
    tutorial_row = (
        _criterion_out(tutorials[0], percentage=TUTORIAL_PERCENTAGE)
        if tutorials else None
    )

    assessment_total = round(
        sum(row["percentage"] or 0.0 for row in assessment_rows), 2
    )
    total = round(
        assessment_total + (TUTORIAL_PERCENTAGE if tutorial_row else 0.0), 2
    )

    return {
        "unit_id": unit.id,
        "unit_code": unit.unit_code,
        "unit_name": unit.unit_name,
        "configured": bool(assessment_rows or tutorial_row),
        "tutorials_enabled": tutorial_row is not None,
        "tutorial": tutorial_row,
        "assessments": assessment_rows,
        "assessment_total_percentage": assessment_total,
        "total_percentage": total,
        "remaining_percentage": round(MAX_TOTAL_PERCENTAGE - total, 2),
        # Stated, not editable. The form shows these so a coordinator can
        # see why the unit's marks stop at 100% while the risk blend
        # clearly weighs more than that.
        "automatic": [_criterion_out(row) for row in fixed],
        "limits": {
            "max_assessments": MAX_ASSESSMENTS,
            "quiz_max_percentage": QUIZ_MAX_PERCENTAGE,
            "tutorial_percentage": TUTORIAL_PERCENTAGE,
            "max_total_percentage": MAX_TOTAL_PERCENTAGE,
        },
        "lock": shape_lock_state(db, unit),
    }


# ---------------------------------------------------------------------
# Deciding how big a proposed change is
# ---------------------------------------------------------------------

def _spec_rows(assessments: list[dict], tutorials_enabled: bool) -> list[tuple]:
    """The comparable identity of a proposed shape, names excluded."""
    rows = [
        (index, _kind_value(item.get("kind")),
         round(float(item.get("percentage") or 0.0), 2))
        for index, item in enumerate(assessments, start=1)
    ]
    return rows + ([("tutorial", None, TUTORIAL_PERCENTAGE)]
                   if tutorials_enabled else [])


def classify_shape_change(current: dict, assessments: list[dict],
                          tutorials_enabled: bool) -> str:
    """
    "none" | "labels_only" | "shape".

    T3's form GETs the whole shape and PUTs the whole shape back, so a
    coordinator who opens a locked unit, reads it and presses Save has
    sent a complete payload that changes nothing. Refusing that with a
    409 would be correct by the letter of the lock and useless in
    practice, and refusing a pure rename would contradict T1's rule that
    a label is not a rule - stated there, and it has to hold here or the
    two write paths disagree about what a change is.

    Names are compared separately from everything else for exactly that
    reason.
    """
    current_rows = _spec_rows(
        [{"kind": row["kind"], "percentage": row["percentage"]}
         for row in current["assessments"]],
        current["tutorials_enabled"],
    )
    if current_rows != _spec_rows(assessments, tutorials_enabled):
        return "shape"

    current_names = [row["name"] for row in current["assessments"]]
    proposed_names = [(item.get("name") or "").strip() for item in assessments]
    if current_names != proposed_names:
        return "labels_only"

    return "none"


# ---------------------------------------------------------------------
# Writing a unit's shape
# ---------------------------------------------------------------------

def replace_unit_shape(db: Session, unit: Unit, assessments: list[dict],
                       tutorials_enabled: bool) -> dict:
    """
    Whole-object replace of a unit's assessments and tutorial setting.

    A REPLACE RATHER THAN PER-ITEM CRUD, ON PURPOSE. Every rule here is
    about the shape as a WHOLE - three items, one 20% quiz cap, one 100%
    budget - and per-item endpoints check each rule against a picture
    that is momentarily wrong. Removing a 40% assignment and adding a 50%
    one is legal as a single act and illegal in either order as two.

    SCOPED BY CATEGORY, WHICH IS THE PART THAT MATTERS. "Replace" here
    means "replace the assessments and the tutorial", NOT "delete every
    criterion not named in the payload". Attendance and Moodle are seeded
    once at unit creation from `risk_constants`, carry 55% of the rule
    blend between them, and are not in this payload - a replace that
    honoured its own name literally would delete both on the first save
    and quietly re-scale every risk score in the unit.

    Rows are matched to payload items by `id` first and by slot second,
    so a rename keeps its history. An item whose slot disappears goes
    through `criteria_service.delete_or_disable_criteria`, which DISABLES
    rather than deletes anything with marks attached - hard-deleting
    would either break the AssessmentEvent foreign key or orphan real
    ingested data.

    Raises CompositionError (-> 400) or ShapeLockedError (-> 409). Stages
    only; the route owns the commit.
    """
    from app.services import criteria_service  # local: avoids an import cycle

    validate_composition(assessments, tutorials_enabled)

    current = get_unit_shape(db, unit)
    change = classify_shape_change(current, assessments, tutorials_enabled)

    if change == "none":
        # Nothing to write, and nothing to refuse. Returning early rather
        # than falling through means an idempotent Save on a locked unit
        # cannot bump a timestamp or burn an unlock window.
        return current

    if change == "shape":
        state = shape_lock_state(db, unit)
        if state["locked"]:
            _refuse(state, "changed")

    existing = _shape_criteria(db, unit.id, (CriteriaCategory.ASSESSMENT,))
    by_id = {row.id: row for row in existing}
    by_slot = {row.sequence_number: row for row in existing if row.sequence_number}
    claimed: set[int] = set()

    for index, item in enumerate(assessments, start=1):
        row = None
        requested_id = item.get("id")
        if requested_id is not None and requested_id in by_id:
            row = by_id[requested_id]
        elif by_slot.get(index) is not None and by_slot[index].id not in claimed:
            row = by_slot[index]

        values = assessment_row_values(item["percentage"])

        if row is None:
            row = Criteria(
                unit_id=unit.id,
                category=CriteriaCategory.ASSESSMENT,
                # A brand-new item starts at the default bar. D1's floors
                # still apply to it the moment a lecturer touches T4's
                # slider - this only decides where it starts.
                threshold=DEFAULT_PASS_PERCENTAGE,
                enabled=True,
            )
            db.add(row)
        elif row.id in claimed:
            # Two payload items pointed at the same stored row. Treat the
            # second as new rather than silently overwriting the first.
            row = Criteria(
                unit_id=unit.id,
                category=CriteriaCategory.ASSESSMENT,
                threshold=DEFAULT_PASS_PERCENTAGE,
                enabled=True,
            )
            db.add(row)

        row.name = (item["name"] or "").strip()
        row.kind = AssessmentKind(_kind_value(item["kind"]))
        row.sequence_number = index
        row.max_score = values["max_score"]
        row.weight = values["weight"]
        # `threshold` is NOT written here, and that is deliberate. It is
        # the lecturer's pass bar (section T4). A whole-object replace
        # that reset it to 50 would silently undo the lecturer's setting
        # every time the coordinator fixed a typo in an item's name.
        if row.id is not None:
            claimed.add(row.id)

    for row in existing:
        if row.id not in claimed:
            criteria_service.delete_or_disable_criteria(db, row)

    _apply_tutorial(db, unit, tutorials_enabled)

    db.flush()
    record_criteria_write(unit, shape_changed=(change == "shape"))
    return get_unit_shape(db, unit)


def _apply_tutorial(db: Session, unit: Unit, enabled: bool) -> None:
    """
    The tutorial toggle. Yes/no only - its 10% is not the coordinator's
    to choose, so nothing here reads a percentage from the payload.

    Re-enabling a previously disabled tutorial reuses the existing row
    rather than creating a second one: two enabled weekly_tut criteria
    would both reach `rule_score_service.build_criterion_inputs` and the
    blend would count tutorials twice.
    """
    from app.services import criteria_service  # local: avoids an import cycle

    rows = (
        db.query(Criteria)
        .filter(
            Criteria.unit_id == unit.id,
            Criteria.category == CriteriaCategory.WEEKLY_TUT,
        )
        .order_by(Criteria.id)
        .all()
    )
    active = [row for row in rows if row.enabled]
    values = tutorial_row_values()

    if enabled:
        row = active[0] if active else (rows[0] if rows else None)
        if row is None:
            row = Criteria(
                unit_id=unit.id,
                name=DEFAULT_TUTORIAL_NAME,
                category=CriteriaCategory.WEEKLY_TUT,
                threshold=DEFAULT_PASS_PERCENTAGE,
                enabled=True,
            )
            db.add(row)
        row.enabled = True
        row.max_score = values["max_score"]
        row.weight = values["weight"]
        # Same reasoning as assessments: `threshold` belongs to T4.
        for duplicate in active[1:]:
            criteria_service.delete_or_disable_criteria(db, duplicate)
        return

    for row in active:
        criteria_service.delete_or_disable_criteria(db, row)