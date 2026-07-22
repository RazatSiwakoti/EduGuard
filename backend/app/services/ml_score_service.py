"""
ML Engine data-wiring layer - Phase 5.2.

Bridges real DB data to ml_engine.py: builds the six-feature dict from
a student's latest AssessmentEvent data, calls predict_risk(), and
stages a RiskScore row (source='ml_model'). Does NOT commit - the
calling route owns the transaction boundary.

Reuses get_latest_criterion_value from rule_score_service.py - both
engines read from the exact same underlying data, just shape it
differently for their own calculation needs.

Two distinct "missing" concepts, tracked separately in missing_notes:
- structural absence: no Criteria row for this category exists at all
  for the unit (e.g. no tutorials) - expected, not a data problem.
- missing student data: the Criteria row exists, but this student has
  no AssessmentEvent for it yet - a real data gap, flagged via
  is_incomplete on the resulting RiskScore.
"""

from sqlalchemy.orm import Session

from app.models.criteria import Criteria
from app.models.assessment_event import AssessmentEvent
from app.models.enums import CriteriaCategory
from app.models.risk_score import RiskScore
from app.services.rule_score_service import get_latest_criterion_value
from app.services.ml_engine import predict_risk
from app.services.ml_engine import predict_risk, build_ml_explanation


def get_latest_criterion_event(db: Session, student_id: int, criteria_id: int):
    """Same lookup as get_latest_criterion_value, but returns the whole
    event - needed here for trend_value, not just score."""
    return (
        db.query(AssessmentEvent)
        .filter(
            AssessmentEvent.student_id == student_id,
            AssessmentEvent.criteria_id == criteria_id,
        )
        .order_by(AssessmentEvent.date.desc(), AssessmentEvent.id.desc())
        .first()
    )


def build_ml_features(db: Session, student_id: int, unit_id: int) -> tuple[dict, list[str]]:
    """Builds the six-feature dict predict_risk() expects, plus a list
    of notes describing anything missing (structural or data-gap)."""
    criteria_rows = (
        db.query(Criteria)
        .filter(Criteria.unit_id == unit_id, Criteria.enabled == True)  # noqa: E712
        .all()
    )
    criteria_by_category = {c.category: c for c in criteria_rows if c.category}
    assessment_criteria = [c for c in criteria_rows if c.category == CriteriaCategory.ASSESSMENT]

    notes: list[str] = []
    features = {
        "moodle_login_count": None,
        "attendance_pct": None,
        "attendance_trend": None,
        "tut_completion_pct": None,
        "tut_trend": None,
        "assessment_avg_pct": None,
    }

    # --- Moodle ---
    moodle_criteria = criteria_by_category.get(CriteriaCategory.MOODLE)
    if moodle_criteria:
        features["moodle_login_count"] = get_latest_criterion_value(db, student_id, moodle_criteria.id)
        if features["moodle_login_count"] is None:
            notes.append("moodle_login_count (no data yet)")
    else:
        notes.append("moodle_login_count (structurally absent)")

    # --- Attendance ---
    attendance_criteria = criteria_by_category.get(CriteriaCategory.ATTENDANCE)
    if attendance_criteria:
        event = get_latest_criterion_event(db, student_id, attendance_criteria.id)
        if event:
            features["attendance_pct"] = event.score
            features["attendance_trend"] = event.trend_value
        else:
            notes.append("attendance_pct/attendance_trend (no data yet)")
    else:
        notes.append("attendance_pct/attendance_trend (structurally absent)")

    # --- Tutorial ---
    tut_criteria = criteria_by_category.get(CriteriaCategory.WEEKLY_TUT)
    if tut_criteria:
        event = get_latest_criterion_event(db, student_id, tut_criteria.id)
        if event:
            features["tut_completion_pct"] = event.score
            features["tut_trend"] = event.trend_value
        else:
            notes.append("tut_completion_pct/tut_trend (no data yet)")
    else:
        notes.append("tut_completion_pct/tut_trend (structurally absent - unit has no tutorials)")

    # --- Assessment average (across however many assessment criteria exist) ---
    if assessment_criteria:
        pct_values = []
        for criteria in assessment_criteria:
            latest = get_latest_criterion_value(db, student_id, criteria.id)
            if latest is not None:
                pct_values.append((latest / criteria.max_score) * 100)
        if pct_values:
            features["assessment_avg_pct"] = sum(pct_values) / len(pct_values)
        if len(pct_values) < len(assessment_criteria):
            notes.append("assessment_avg_pct (some assessment items missing data)")
    else:
        notes.append("assessment_avg_pct (structurally absent - unit has no assessment criteria)")

    return features, notes



def compute_and_stage_ml_score(
    db: Session, student_id: int, unit_id: int, checkpoint_week: int = 8
) -> RiskScore:
    features, notes = build_ml_features(db, student_id, unit_id)
    result = predict_risk(features)

    incomplete_notes = [n for n in notes if "no data yet" in n]
    top_probability = max(result.probabilities.values())

    risk_score = RiskScore(
        student_id=student_id,
        unit_id=unit_id,
        source="ml_model",
        risk_score=top_probability,
        risk_level=result.tier,
        checkpoint_week=checkpoint_week,
        is_incomplete=len(incomplete_notes) > 0,
        missing_criteria=", ".join(incomplete_notes) if incomplete_notes else None,
        explanation=build_ml_explanation(features, result.tier),
    )
    db.add(risk_score)
    return risk_score