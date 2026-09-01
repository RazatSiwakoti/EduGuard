"""
Pydantic schemas for the lecturer analytics dashboard (Phase 6.2).

Deliberately ONE flat payload rather than several pre-aggregated
endpoints. The dashboard has two live filters (unit + risk level) that
cross-filter every chart at once; aggregating server-side would mean a
network round-trip on every single filter click. Sending one flat row
per student lets React recompute all six visuals in a `useMemo` with
zero refetch, which is what makes the dashboard feel instant.

Payload size is a non-issue at this scale: one lecturer's whole cohort
across every unit they teach is a few hundred rows, and each row is a
handful of numbers.

Naming note: `final_tier` is Optional because FinalVerdict.final_tier is
NULL by design whenever requires_review is True - a genuine safe-vs-
high_risk disagreement between the two engines gets NO automatic verdict
until a lecturer resolves it. The frontend renders that as its own
"Needs Review" bucket rather than hiding those students.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DashboardUnit(BaseModel):
    """One unit the requesting lecturer is assigned to. Populates the
    unit filter dropdown and the 'Risk by Unit' chart's axis."""

    id: int
    unit_code: str
    full_code: str
    unit_name: str
    year: Optional[int] = None
    teaching_period: Optional[str] = None
    level: Optional[str] = None
    enrolled_count: int


class DashboardCriterionScore(BaseModel):
    """
    A single student's latest value for one criterion of their unit.

    `score` is on the criterion's own native scale - a PERCENTAGE for
    attendance/tutorials/assessments, but a RAW LOGIN COUNT for Moodle.
    Those are not comparable on a shared axis, which is exactly why the
    frontend normalises everything to "% of threshold" before charting.
    Both the raw score and its threshold are sent so the tooltip can
    still show the real number.

    `trend_value` is only ever populated for ATTENDANCE and WEEKLY_TUT
    (see AssessmentEvent.trend_value) - NULL for assessments and Moodle.
    Negative means the student is declining across the checkpoint window.
    """

    criteria_id: int
    name: str
    category: Optional[str] = None
    score: float
    threshold: float
    max_score: float
    trend_value: Optional[float] = None


class DashboardStudent(BaseModel):
    """
    One enrolled student in one unit, with their latest risk picture.

    A student enrolled in two of this lecturer's units appears TWICE -
    once per unit - because risk is always computed per unit, never
    globally. The frontend's `student_id` + `unit_id` pair is the real
    identity of a row.
    """

    student_id: int
    student_number: str
    name: str
    email: Optional[str] = None
    program: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None

    unit_id: int
    unit_code: str

    # False when the student is enrolled but the pipeline has never run
    # for them (uploaded dataset, never hit "Run Analysis"). Every risk
    # field below is None in that case - the frontend surfaces these as
    # a distinct "Not Analysed" bucket instead of silently dropping them.
    analysed: bool = False

    final_tier: Optional[str] = None        # "safe" | "low_risk" | "high_risk" | None
    requires_review: bool = False
    reason: Optional[str] = None
    checkpoint_week: Optional[int] = None
    computed_at: Optional[datetime] = None

    # The two engines' independent verdicts, kept separate so the
    # rule-vs-ML agreement matrix can show where they diverged.
    rule_tier: Optional[str] = None
    rule_score: Optional[float] = None
    ml_tier: Optional[str] = None
    ml_score: Optional[float] = None

    # True when either engine flagged missing input data - such a score
    # is still shown but should not be read with full confidence.
    is_incomplete: bool = False

    criteria: list[DashboardCriterionScore] = []


class LecturerDashboardResponse(BaseModel):
    """Everything the dashboard needs, in a single request."""

    units: list[DashboardUnit]
    students: list[DashboardStudent]
    # Echoed back so the UI can label charts honestly ("Week 8 checkpoint")
    # instead of hardcoding a number the backend might later change.
    checkpoint_week: int

class DashboardUnitCriterion(BaseModel):
    """
    A criterion as CONFIGURED on a unit, independent of whether any
    student has data for it.

    This exists because DashboardStudent.criteria only ever carries
    criteria a student actually has an AssessmentEvent for - a
    deliberate choice, since a missing mark and a mark of zero mean
    very different things. The side effect is that the frontend can
    count how many assessments a student HAS been marked for, but has
    no way to know how many the unit defines. Two marks out of what?

    Sending the unit's own criteria answers that, and answers it per
    unit: one unit may run three assessments and another just one.
    """

    id: int
    name: str
    category: Optional[str] = None
    threshold: float
    max_score: float


class DashboardUnit(BaseModel):
    """One unit the requesting lecturer is assigned to. Populates the
    unit filter dropdown and the 'Risk by Unit' chart's axis."""

    id: int
    unit_code: str
    unit_name: str
    year: Optional[int] = None
    teaching_period: Optional[str] = None
    level: Optional[str] = None
    enrolled_count: int

    # Empty on GET /lecturer/units, which exists precisely to stay
    # lightweight. Only the dashboard payload populates it, because
    # only the students table needs the denominator.
    criteria: list[DashboardUnitCriterion] = []