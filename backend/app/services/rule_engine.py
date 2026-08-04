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
    TUTORIAL_THRESHOLD_FLOOR,
    SAFE_CUTOFF,
    HIGH_RISK_CUTOFF,
    TUTORIAL_STATUS_CREDIT,
)


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

    Criteria with actual=None (structurally absent, e.g. no tutorials) are
    excluded from BOTH the numerator and denominator - this is what makes
    weights automatically rescale for units missing a category, with no
    special-casing required.
    """
    breakdown: list[CriterionBreakdown] = []
    weighted_badness_sum = 0.0
    total_weight_used = 0.0

    for criterion in criteria:
        if criterion.actual is None:
            continue  # structurally absent - skip entirely, don't count its weight

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
    )


def validate_lecturer_threshold(category: str, proposed_threshold: float) -> None:
    """
    Enforces the global minimum floor for lecturer-adjustable thresholds.
    Call this from the Criteria create/update service BEFORE the row is
    written. Attendance and Moodle should never reach this function since
    they aren't lecturer-editable at the API layer.
    """
    floors = {
        "assessment": ASSESSMENT_THRESHOLD_FLOOR,
        "tutorial": TUTORIAL_THRESHOLD_FLOOR,
    }

    floor = floors.get(category.lower())
    if floor is not None and proposed_threshold < floor:
        raise ValueError(
            f"{category.title()} threshold cannot be set below {floor}% "
            f"(proposed: {proposed_threshold}%)."
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