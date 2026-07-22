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
from app.services.rule_engine import CriterionInput, compute_rule_based_risk


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
        latest_value = get_latest_criterion_value(db, student_id, criteria.id)
        category_label = criteria.category.value if criteria.category else criteria.name

        if latest_value is None:
            missing_categories.append(category_label)

        inputs.append(
            CriterionInput(
                category=category_label,
                actual=latest_value,
                threshold=criteria.threshold,
                weight=criteria.weight,
            )
        )

    return inputs, missing_categories


def compute_and_stage_rule_score(
    db: Session, student_id: int, unit_id: int, checkpoint_week: int = 8
) -> RiskScore:
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