"""
Rule Engine data-wiring layer - Phase 5.2.

Bridges real DB data to the pure calculation logic in rule_engine.py:
fetches a student's live Criteria + AssessmentEvent data, builds
CriterionInput objects, runs the calculation, and stages a RiskScore
row (source='rule_based'). Does NOT commit - the calling route owns
the transaction boundary, per this project's established convention.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.criteria import Criteria
from app.models.assessment_event import AssessmentEvent
from app.models.risk_score import RiskScore
from app.services.rule_engine import (
    CriterionInput,
    compute_rule_based_risk,
    build_rule_explanation,
)


def get_latest_criterion_value(db: Session, student_id: int, criteria_id: int) -> Optional[float]:
    """
    AssessmentEvent is insert-only - a correction is a NEW row, not an
    update to an old one. So "the student's current value" for a
    criterion is always the MOST RECENT event, not a sum or average of
    every row ever ingested for them.
    """
    event = (
        db.query(AssessmentEvent)
        .filter(
            AssessmentEvent.student_id == student_id,
            AssessmentEvent.criteria_id == criteria_id,
        )
        .order_by(AssessmentEvent.date.desc(), AssessmentEvent.id.desc())
        .first()
    )
    return event.score if event else None


def normalise_to_percentage(value: Optional[float], criteria: Criteria) -> Optional[float]:
    """
    Converts a raw stored score onto the 0-100 scale the rule engine's
    thresholds are expressed in.

    WHY THIS EXISTS - the scale bug it fixes
    ----------------------------------------
    AssessmentEvent.score is stored RAW: a quiz marked out of 20 stores
    15, not 75. CriterionInput's own docstring requires `actual` to be
    "already normalised to a comparable scale (percentage for
    Attendance/Assessment/Tutorial)" - but this layer used to pass the
    raw value straight through.

    The ML engine, meanwhile, has always normalised: ml_score_service
    computes (latest / criteria.max_score) * 100 for assessments. So the
    two engines were reading the SAME database row on DIFFERENT scales.

    A student scoring 15/20 against a threshold of 45:
        rule engine saw  15 vs 45   -> badly failing -> high_risk
        ML engine saw    75%        -> fine          -> safe
        hybrid layer     safe vs high_risk           -> requires_review

    Every assessment not marked out of 100 produced a guaranteed false
    review. Normalising here makes both engines agree on what the number
    MEANS, so any remaining disagreement is a real modelling difference
    rather than an arithmetic one.

    Attendance, tutorials and Moodle are seeded with max_score=100, so
    this is a no-op for them - (value / 100) * 100 == value. Applying it
    uniformly rather than special-casing assessments means any future
    category gets correct behaviour for free instead of silently
    inheriting the bug.
    """
    if value is None:
        return None

    # A zero or missing max_score would divide by zero. Passing the raw
    # value through is the safer failure: it preserves the old behaviour
    # rather than inventing a number.
    if not criteria.max_score:
        return value

    return (value / criteria.max_score) * 100


def build_criterion_inputs(
    db: Session, student_id: int, unit_id: int
) -> tuple[list[CriterionInput], list[str]]:
    """
    Builds the exact input list compute_rule_based_risk() expects.

    Only ENABLED Criteria rows that exist for this unit are considered -
    a criterion that was never created for this unit (e.g. no Weekly Tut)
    never reaches this function at all, which is what makes structural
    absence handle itself automatically.

    A None actual value here can therefore only mean one thing: this
    criterion DOES apply to the unit, but this specific student has no
    AssessmentEvent for it yet. That's missing data, not structural
    absence - so it's tracked separately in missing_categories and
    surfaced to the caller, rather than silently treated the same way.
    """
    criteria_rows = (
        db.query(Criteria)
        .filter(Criteria.unit_id == unit_id, Criteria.enabled == True)  # noqa: E712
        .all()
    )

    inputs: list[CriterionInput] = []
    missing_categories: list[str] = []

    for criteria in criteria_rows:
        raw_value = get_latest_criterion_value(db, student_id, criteria.id)
        category_label = criteria.category.value if criteria.category else criteria.name

        if raw_value is None:
            missing_categories.append(category_label)

        # Normalised BEFORE it reaches the engine, so `actual` and
        # `threshold` are always on the same 0-100 scale - and so this
        # engine and the ML engine read the same row the same way.
        # See normalise_to_percentage() for the bug this prevents.
        inputs.append(
            CriterionInput(
                category=category_label,
                actual=normalise_to_percentage(raw_value, criteria),
                threshold=criteria.threshold,
                weight=criteria.weight,
            )
        )

    return inputs, missing_categories


def compute_and_stage_rule_score(
    db: Session, student_id: int, unit_id: int, checkpoint_week: int = 8
) -> RiskScore:
    """
    Full pipeline: fetch -> calculate -> stage a RiskScore row.
    Does NOT commit - the calling route commits.
    """
    criterion_inputs, missing_categories = build_criterion_inputs(db, student_id, unit_id)
    result = compute_rule_based_risk(criterion_inputs)

    risk_score = RiskScore(
        student_id=student_id,
        unit_id=unit_id,
        source="rule_based",
        risk_score=result.combined_score,
        risk_level=result.tier.value,
        checkpoint_week=checkpoint_week,
        is_incomplete=len(missing_categories) > 0,
        missing_criteria=", ".join(missing_categories) if missing_categories else None,
        explanation=build_rule_explanation(result),
    )
    db.add(risk_score)
    return risk_score