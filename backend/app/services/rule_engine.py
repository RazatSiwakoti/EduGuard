"""
Rule Engine - Phase 5.2

Pure, DB-independent risk calculation logic for EduGuard's rule-based engine.
This module ONLY does calculation - no database reads or writes. The calling
service/route is responsible for fetching raw student data, building
CriterionInput objects, calling compute_rule_based_risk(), and persisting
the result to RiskScore (source='rule_based').

Also hosts the weekly-aggregation helpers used by ingestion_service.py -
percentage AND trend calculations for Attendance/Weekly Tut, since both
the rule engine and the ML engine's trend feature need the exact same
underlying weekly data, just summarised differently.

All fixed numeric constants live in app.core.risk_constants - the single
source of truth shared with unit_service.py's Criteria seeding, so the
two can never drift out of sync.

Locked design:
- Per-criterion badness: shortfall relative to threshold, capped at 1.0
- Combine: weighted average across ENABLED/PRESENT criteria only
- Final bucket cutoffs: <0.15 safe | 0.15-0.30 low_risk | >=0.30 high_risk
- Tutorial weekly status -> completion %: submitted=1.0, late=0.8, not_submitted=0.0
- Unsubmitted assessments are always literal 0, never NULL
- Structural absence (e.g. no tutorials in this unit) = actual is None -> excluded entirely
- Trend calculations mirror the ML training notebook's formula exactly:
  attendance trend = (weeks 5-7 avg - weeks 1-3 avg) * 100, week 4 excluded
  tutorial trend = (weeks 5-6 avg - weeks 2-3 avg) * 100, weeks 4 & 7 excluded
"""

from dataclasses import dataclass
from enum import Enum

from app.core.risk_constants import (
    ASSESSMENT_THRESHOLD_FLOOR,
    FIXED_ATTENDANCE_THRESHOLD,
    FIXED_MOODLE_THRESHOLD,
    TUTORIAL_THRESHOLD_FLOOR,
    SAFE_CUTOFF,
    HIGH_RISK_CUTOFF,
    MIN_EVIDENCE_COVERAGE,
    TUTORIAL_STATUS_CREDIT,
)
from app.models.enums import CriteriaCategory


class RiskTier(str, Enum):
    SAFE = "safe"
    LOW_RISK = "low_risk"
    HIGH_RISK = "high_risk"


@dataclass
class CriterionInput:
    """
    One criterion's data for a single student, already normalised to a
    comparable scale (percentage for Attendance/Assessment/Tutorial,
    raw count for Moodle).

    actual=None means this criterion is structurally absent for this unit
    (e.g. no tutorials) and must be excluded entirely - NOT treated as zero.
    """
    category: str           # "attendance" | "assessment" | "tutorial" | "moodle"
    actual: float | None    # student's raw value, already normalised
    threshold: float        # this criterion's threshold (fixed or lecturer-set)
    weight: float            # lecturer-assigned importance


@dataclass
class CriterionBreakdown:
    """One line of the explainability breakdown returned alongside the tier."""
    category: str
    actual: float | None
    threshold: float
    weight: float
    badness: float


@dataclass
class RuleEngineResult:
    tier: RiskTier
    combined_score: float
    breakdown: list[CriterionBreakdown]

    # ------------------------------------------------------------------
    # HOW MUCH EVIDENCE THIS SCORE IS ACTUALLY BASED ON.
    #
    # `combined_score` is a weighted average over the criteria that had
    # data. Without these three fields there is no way to tell a 0.0
    # earned across every criterion from a 0.0 earned across one of
    # five - and those two numbers mean opposite things.
    # ------------------------------------------------------------------

    #: Total weight of every criterion that applies to this unit.
    total_weight: float = 0.0
    #: Weight of the criteria that actually had a value.
    scored_weight: float = 0.0

    @property
    def coverage(self) -> float:
        """
        Share of the unit's weight the score is based on, 0.0 to 1.0.

        1.0 means every applicable criterion had data. Anything less
        means the blend was rescaled onto a subset, and the smaller this
        is the less `combined_score` is entitled to be believed.
        """
        if self.total_weight <= 0:
            return 0.0
        return self.scored_weight / self.total_weight

    @property
    def has_enough_evidence(self) -> bool:
        """Whether this score may be reported as a tier at all."""
        return self.coverage >= MIN_EVIDENCE_COVERAGE


def calculate_badness(actual: float, threshold: float) -> float:
    """
    Core shortfall formula, shared by every criterion type.

    Meeting or exceeding the threshold contributes zero badness. Falling
    below it contributes badness proportional to how far below, relative
    to the threshold itself - capped at 1.0 so a total collapse (e.g. 0)
    never exceeds maximum badness.
    """
    if threshold <= 0:
        # Defensive guard against a zero/negative threshold (would divide
        # by zero below). Treat as "no meaningful bar set" -> no badness.
        return 0.0

    if actual >= threshold:
        return 0.0

    shortfall = (threshold - actual) / threshold
    return min(shortfall, 1.0)


def calculate_tutorial_completion_pct(weekly_statuses: list[str]) -> float:
    """
    Converts weekly tutorial statuses ("submitted"/"late"/"not_submitted")
    into one completion percentage. "late" counts as 0.8 credit, matching
    the ML training label formula.
    """
    if not weekly_statuses:
        return 0.0

    total_credit = sum(
        TUTORIAL_STATUS_CREDIT.get(status, 0.0) for status in weekly_statuses
    )
    return (total_credit / len(weekly_statuses)) * 100.0


def calculate_attendance_pct(weekly_attended: list[bool]) -> float:
    """Converts weekly attendance booleans into a single percentage."""
    if not weekly_attended:
        return 0.0

    attended_weeks = sum(1 for attended in weekly_attended if attended)
    return (attended_weeks / len(weekly_attended)) * 100.0


def calculate_attendance_trend(weekly_attended: list[bool]) -> float | None:
    """
    Mirrors the ML training notebook's trend feature exactly: average of
    weeks 5-7 minus average of weeks 1-3, as a percentage-point
    difference. Week 4 is deliberately excluded from both halves -
    matches training, so live serving can't skew from what was learned.
    Requires exactly 7 weekly values in week order. Returns None otherwise.
    """
    if len(weekly_attended) != 7:
        return None
    early = weekly_attended[0:3]   # weeks 1-3
    late = weekly_attended[4:7]    # weeks 5-7
    early_pct = sum(1 for a in early if a) / len(early)
    late_pct = sum(1 for a in late if a) / len(late)
    return (late_pct - early_pct) * 100


def calculate_tutorial_completion_trend(weekly_statuses: list[str]) -> float | None:
    """
    Mirrors the ML training notebook's tutorial trend feature exactly:
    average credit of weeks 5-6 minus average credit of weeks 2-3.
    Weeks 4 and 7 are deliberately excluded from both halves - matches
    training. Requires exactly 6 weekly values ordered week 2 through
    week 7. Returns None otherwise.
    """
    if len(weekly_statuses) != 6:
        return None
    # Index: 0=w2, 1=w3, 2=w4, 3=w5, 4=w6, 5=w7
    early = weekly_statuses[0:2]
    late = weekly_statuses[3:5]
    early_credit = sum(TUTORIAL_STATUS_CREDIT.get(s, 0.0) for s in early) / len(early)
    late_credit = sum(TUTORIAL_STATUS_CREDIT.get(s, 0.0) for s in late) / len(late)
    return (late_credit - early_credit) * 100


def bucket_score(combined_score: float) -> RiskTier:
    """Applies the fixed, global bucket cutoffs to a combined badness score."""
    if combined_score < SAFE_CUTOFF:
        return RiskTier.SAFE
    if combined_score < HIGH_RISK_CUTOFF:
        return RiskTier.LOW_RISK
    return RiskTier.HIGH_RISK


def compute_rule_based_risk(criteria: list[CriterionInput]) -> RuleEngineResult:
    """
    Main entry point. Takes every criterion applicable to this student's
    unit, computes each one's badness, blends them by weight, and buckets
    the result into a final tier.

    A criterion with actual=None is excluded from both the numerator and
    the denominator, so the remaining weights rescale automatically.

    THAT RESCALING IS ONLY SAFE WHEN THE CALLER TELLS YOU HOW MUCH IT
    RESCALED BY, which is what `total_weight` and `coverage` are for.
    This function's previous docstring called every None "structurally
    absent, e.g. no tutorials" and left it there. That is true of a unit
    with no tutorial criterion - but such a criterion never reaches this
    list at all, because `build_criterion_inputs` only builds inputs from
    Criteria rows that EXIST for the unit. So in the real pipeline a None
    here has only ever meant one thing: this criterion applies and this
    student has no data for it.

    Rescaling silently over that produced the defect this now reports:
    a student with no assessment marks was scored across attendance and
    tutorials alone, earned a perfect 0.0 badness, and was returned SAFE
    while two thirds of the unit's weight went unexamined. A student with
    NO data at all scored 0.0 too - because zero is not a neutral value
    in this scale, it is the best one obtainable.

    The tier is still computed and returned. Deciding whether the
    evidence is sufficient to ACT on it belongs to the caller - see
    `has_enough_evidence` and final_verdict_service.
    """
    
    breakdown: list[CriterionBreakdown] = []
    weighted_badness_sum = 0.0
    total_weight_used = 0.0
    # Every criterion in this list applies to the unit, whether or not
    # this student has data for it. That is the denominator coverage is
    # measured against.
    total_weight_applicable = sum(criterion.weight for criterion in criteria)

    for criterion in criteria:
        if criterion.actual is None:
            # No data for this student. Skipped from the blend, but its
            # weight still counts towards what SHOULD have been scored.
            continue

        badness = calculate_badness(criterion.actual, criterion.threshold)
        weighted_badness_sum += criterion.weight * badness
        total_weight_used += criterion.weight

        breakdown.append(
            CriterionBreakdown(
                category=criterion.category,
                actual=criterion.actual,
                threshold=criterion.threshold,
                weight=criterion.weight,
                badness=badness,
            )
        )

    # Guard against divide-by-zero if somehow no criteria applied at all
    combined_score = (
        weighted_badness_sum / total_weight_used if total_weight_used > 0 else 0.0
    )

    return RuleEngineResult(
        tier=bucket_score(combined_score),
        combined_score=combined_score,
        breakdown=breakdown,
        total_weight=total_weight_applicable,
        scored_weight=total_weight_used,
    )

#: Floors by CriteriaCategory VALUE, not by an English word.
#:
#: This dict was previously keyed "tutorial" while the enum value is
#: "weekly_tut", so `floors.get("weekly_tut")` returned None and tutorial
#: thresholds were silently accepted at any value, including zero. The
#: function had no callers, so nothing ever surfaced it. Keying off the
#: enum's own values is what stops that recurring.
THRESHOLD_FLOORS: dict[str, float] = {
    CriteriaCategory.ASSESSMENT.value: ASSESSMENT_THRESHOLD_FLOOR,
    CriteriaCategory.WEEKLY_TUT.value: TUTORIAL_THRESHOLD_FLOOR,
}

#: Categories whose threshold is a system constant, not a lecturer's
#: choice. Listed explicitly rather than left to fall through the
#: floors lookup: "no floor configured" and "not editable at all" are
#: different rules, and the old code could not tell them apart.
FIXED_THRESHOLDS: dict[str, float] = {
    CriteriaCategory.ATTENDANCE.value: FIXED_ATTENDANCE_THRESHOLD,
    CriteriaCategory.MOODLE.value: FIXED_MOODLE_THRESHOLD,
}

#: The default every unit starts at. A lecturer may lower an adjustable
#: threshold to its floor, never raise it above this.
DEFAULT_THRESHOLD = 50.0


def validate_lecturer_threshold(category, proposed_threshold: float) -> None:
    """
    Enforces the rules on a lecturer-set threshold. Raises ValueError.

    Call BEFORE the row is written, from both create and update.

    THREE OUTCOMES, DELIBERATELY DISTINCT:

    - Assessment and weekly tutorials are adjustable DOWNWARD ONLY, from
      the 50% default to their own floor (45% and 40%). Raising the bar
      is refused too: a lecturer quietly making their unit harder to
      pass changes what "at risk" means without anyone being told.

    - Attendance and Moodle are FIXED. Any attempt to change them is
      refused rather than ignored, because silently discarding a write
      the caller believes succeeded is worse than an error.

    - A criterion with no category has no floor. It is already reported
      as a caveat ("invisible to the ML model"); section D2 stops them
      being created at all.

    Accepts a CriteriaCategory or its string value, so callers do not
    have to remember which one they are holding.
    """
    if category is None:
        return

    key = getattr(category, "value", category)
    key = str(key).lower()

    fixed = FIXED_THRESHOLDS.get(key)
    if fixed is not None:
        raise ValueError(
            f"The {key.replace('_', ' ')} threshold is fixed at {fixed:g} and "
            "cannot be changed."
        )

    floor = THRESHOLD_FLOORS.get(key)
    if floor is None:
        return

    if proposed_threshold < floor:
        raise ValueError(
            f"Threshold cannot be set below {floor:g}% "
            f"(proposed: {proposed_threshold:g}%)."
        )

    if proposed_threshold > DEFAULT_THRESHOLD:
        raise ValueError(
            f"Threshold cannot be set above the {DEFAULT_THRESHOLD:g}% default "
            f"(proposed: {proposed_threshold:g}%)."
        )

def build_rule_explanation(result: RuleEngineResult, top_n: int = 3) -> str:
    """
    Plain-language explanation of the rule engine's decision, built from
    the per-criterion badness breakdown - names the top N criteria
    actually driving the score (ranked by weight x badness, so a
    high-weight moderate problem outranks a low-weight severe one,
    consistent with how they're actually combined).
    """
    contributing = [b for b in result.breakdown if b.badness > 0]
    contributing.sort(key=lambda b: b.weight * b.badness, reverse=True)
    top = contributing[:top_n]

    if not top:
        return "Rule engine: all tracked criteria met their thresholds - no risk factors identified."

    parts = [f"{b.category} at {b.actual:.1f} (threshold {b.threshold:.1f})" for b in top]
    return "Rule engine flagged: " + "; ".join(parts) + "."