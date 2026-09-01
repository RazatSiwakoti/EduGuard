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
            # "no data yet" is the phrase compute_and_stage_ml_score
            # greps for to decide `is_incomplete`. This branch used to
            # read "(some assessment items missing data)" instead, so a
            # student with NO assessment marks at all produced
            # is_incomplete=False - the one flag that would have caught
            # them, disabled by a substring that did not match.
            #
            # Detecting incompleteness by searching English prose was the
            # real fault. `missing_feature_keys` below is the fix; the
            # wording is aligned as well so the two cannot drift again.
            notes.append(
                f"assessment_avg_pct (no data yet - "
                f"{len(assessment_criteria) - len(pct_values)} of "
                f"{len(assessment_criteria)} assessment items unmarked)"
            )
    else:
        notes.append("assessment_avg_pct (structurally absent - unit has no assessment criteria)")

        return features, notes


def missing_feature_keys(features: dict) -> list[str]:
    """Every model input this student has no value for."""
    return [key for key, value in features.items() if value is None]


def structural_feature_keys(notes: list[str]) -> set[str]:
    """
    The features this UNIT does not have at all.

    Read from the notes because that is where `build_ml_features`
    already records the distinction. A unit with no tutorial criterion
    produces a None `tut_completion_pct` that is not a gap in the
    student's record, and counting it against them would push every
    student in a tutorial-less unit below the coverage floor.
    """
    structural: set[str] = set()
    for note in notes:
        if "structurally absent" not in note:
            continue
        # Notes are "key/key (reason)" or "key (reason)".
        head = note.split("(")[0].strip()
        structural.update(part.strip() for part in head.split("/") if part.strip())
    return structural


# Which unit category each model input is drawn from. Two features can
# share one criterion - attendance yields both a percentage and a trend -
# so coverage is measured over CATEGORIES rather than over features, or a
# single attendance mark would be counted twice.
FEATURE_CATEGORY: dict[str, str] = {
    "moodle_login_count": CriteriaCategory.MOODLE,
    "attendance_pct": CriteriaCategory.ATTENDANCE,
    "attendance_trend": CriteriaCategory.ATTENDANCE,
    "tut_completion_pct": CriteriaCategory.WEEKLY_TUT,
    "tut_trend": CriteriaCategory.WEEKLY_TUT,
    "assessment_avg_pct": CriteriaCategory.ASSESSMENT,
}

# A trend is DERIVED from the same event as its score, never marked
# separately. It is None when a student has exactly one observation,
# which means "too early to see a direction", not "no evidence".
# Counting it as a gap would flag every student in week 1.
TREND_FEATURES = {"attendance_trend", "tut_trend"}


def category_weights(db: Session, unit_id: int) -> dict[str, float]:
    """{category: summed weight of its enabled criteria} for one unit."""
    rows = (
        db.query(Criteria)
        .filter(Criteria.unit_id == unit_id, Criteria.enabled == True)  # noqa: E712
        .all()
    )
    weights: dict[str, float] = {}
    for criteria in rows:
        if not criteria.category:
            continue
        weights[criteria.category] = weights.get(criteria.category, 0.0) + (criteria.weight or 0.0)
    return weights


def weighted_coverage(
    db: Session, unit_id: int, incomplete_keys: list[str], structural: set[str]
) -> float:
    """
    The share of the unit's WEIGHT this prediction actually saw.

    CORRECTED, and the original is worth recording. This was
    `present features / applicable features`, defended in a comment
    saying each engine should report coverage of the inputs it takes.
    That argument does not survive contact with the floor:
    `MIN_EVIDENCE_COVERAGE` is ONE number compared against BOTH engines,
    so both have to be measuring the same quantity.

    Mei Fujita is the proof. Missing both assessments cost her 65% of her
    unit's weight but only one model input out of six, so the feature
    count read 83%, cleared a 70% floor, and the ML half of the gate did
    nothing on the exact record it was written for. The rule engine
    caught her regardless - which is why this would never have been
    noticed: a redundant guard that silently abstains.
    """
    weights = category_weights(db, unit_id)

    applicable: dict[str, float] = {}
    for feature, category in FEATURE_CATEGORY.items():
        if feature in structural:
            continue
        weight = weights.get(category)
        if weight is not None:
            applicable[category] = weight

    total = sum(applicable.values())
    if total <= 0:
        return 0.0

    missing_categories = {
        FEATURE_CATEGORY[key] for key in incomplete_keys if key in FEATURE_CATEGORY
    }
    present = sum(
        weight for category, weight in applicable.items()
        if category not in missing_categories
    )
    return present / total



def compute_and_stage_ml_score(
    db: Session, student_id: int, unit_id: int, checkpoint_week: int = 8
) -> RiskScore:
    features, notes = build_ml_features(db, student_id, unit_id)
    result = predict_risk(features)

    # STRUCTURED, not a substring search over English.
    #
    # This was `[n for n in notes if "no data yet" in n]`, which silently
    # stopped working for the one category that mattered most the moment
    # a note was worded differently. Comparing sets of feature keys
    # cannot drift with prose.
    missing = missing_feature_keys(features)
    structural = structural_feature_keys(notes)
    # A feature the UNIT does not have is not a gap in this student's
    # record - a unit with no tutorials is not a student who skipped them.
    # A trend is excluded for the reason given at TREND_FEATURES: it is
    # derived from the same event as its score, so its absence means one
    # observation rather than none.
    incomplete_keys = [
        key for key in missing
        if key not in structural and key not in TREND_FEATURES
    ]

    coverage = weighted_coverage(db, unit_id, incomplete_keys, structural)

    top_probability = max(result.probabilities.values())

    risk_score = RiskScore(
        student_id=student_id,
        unit_id=unit_id,
        source="ml_model",
        risk_score=top_probability,
        risk_level=result.tier,
        checkpoint_week=checkpoint_week,
        is_incomplete=len(incomplete_keys) > 0,
        missing_criteria=", ".join(incomplete_keys) if incomplete_keys else None,
        # The SAME measure the rule engine writes - share of unit weight
        # seen - because one floor is compared against both.
        coverage=coverage,
        explanation=build_ml_explanation(features, result.tier),
    )
    db.add(risk_score)
    return risk_score
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