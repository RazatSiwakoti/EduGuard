"""
Pydantic schemas for the per-student detail card (Phase 7.6b).

WHY THIS EXISTS RATHER THAN REUSING THE DASHBOARD PAYLOAD
---------------------------------------------------------
GET /lecturer/dashboard already carries most of a student's picture, and
the students TABLE is built entirely from it. The card needs three
things that payload structurally cannot give:

  1. `RiskScore.explanation` - the rule engine's per-criterion breakdown
     and the ML model's SHAP-derived reasoning. Never sent to the
     dashboard, and not reconstructable from what is.
  2. Criteria the student has NO data for. The dashboard deliberately
     omits those (a missing mark and a zero mean different things), but
     the card's whole job is showing what is missing, so it sends every
     criterion the unit defines with a null score where there is no
     event.
  3. `weekly_values` - the per-week cells behind the attendance and
     tutorial percentages. Far too heavy to ship for a whole cohort,
     exactly right for one student.

Sending these on the dashboard payload instead would multiply its size
for every student a lecturer never opens.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class StudentCriterionDetail(BaseModel):
    """
    One criterion of the unit, and this student's standing against it.

    UNLIKE the dashboard's equivalent, a criterion with no recorded event
    is still returned, with `score = None`. That distinction is the point
    of the card: "no mark recorded" and "scored zero" look identical in
    an aggregate and mean completely different things to a lecturer.
    """

    criteria_id: int
    name: str
    category: Optional[str] = None
    threshold: float
    max_score: float

    # None = no AssessmentEvent exists for this student and criterion.
    score: Optional[float] = None
    # Only ever set for attendance / weekly_tut.
    trend_value: Optional[float] = None

    # The normalised weekly cells behind `score`:
    #   attendance  -> 7 booleans      (W1-W7)
    #   weekly_tut  -> 6 status strings (W2-W7)
    # None for assessments and Moodle, which have no weekly dimension,
    # and None for anything ingested before Phase 7.6b - those cells
    # were discarded at the time and cannot be recovered.
    weekly_values: Optional[list] = None

    recorded_at: Optional[datetime] = None


class StudentEngineDetail(BaseModel):
    """
    One engine's independent verdict, kept separate from the other so
    the card can show where they diverged.

    ⚠️ `score` MEANS SOMETHING DIFFERENT PER ENGINE and the two must
    never be plotted on a shared scale:
      - rule_based: the combined weighted BADNESS score. Higher = worse.
      - ml_model:   the predicted class PROBABILITY, i.e. the model's
                    confidence in the tier it chose. Higher = more sure,
                    which is not the same as more at risk.
    `score_kind` is sent so the frontend labels each one correctly
    instead of guessing from the number.
    """

    tier: str
    score: float
    score_kind: str  # "badness" | "confidence"
    is_incomplete: bool = False
    missing_criteria: Optional[str] = None
    explanation: Optional[str] = None
    computed_at: Optional[datetime] = None


class StudentReviewDetail(BaseModel):
    """
    One recorded lecturer decision on an engine disagreement.

    `rule_tier` and `ml_tier` are the pair this decision was made ABOUT.
    They are sent so the card can explain a decision that no longer
    applies - "you resolved this when the model said high risk; it now
    says low risk" - rather than silently asking again as if the
    lecturer had never decided anything.
    """

    id: int
    decision: str
    comment: Optional[str] = None
    rule_tier: str
    ml_tier: str
    reviewed_by: int
    reviewer_name: Optional[str] = None
    created_at: Optional[datetime] = None


class StudentNoteDetail(BaseModel):
    """The requesting lecturer's own notes. Never another lecturer's."""

    body: str
    updated_at: Optional[datetime] = None


class StudentDetailResponse(BaseModel):
    """Everything the student card renders, in one request."""

    student_id: int
    student_number: str
    name: str
    email: Optional[str] = None
    program: Optional[str] = None

    unit_id: int
    unit_code: str
    unit_name: str
    enrolled_at: Optional[datetime] = None

    checkpoint_week: int

    # False when the student is enrolled but the pipeline has never
    # produced a verdict for them. Every field below is None in that
    # case and the card says so plainly.
    analysed: bool = False
    final_tier: Optional[str] = None
    requires_review: bool = False
    reason: Optional[str] = None
    computed_at: Optional[datetime] = None

    rule: Optional[StudentEngineDetail] = None
    ml: Optional[StudentEngineDetail] = None

    # EVERY enabled criterion on the unit, including ones with no data.
    criteria: list[StudentCriterionDetail] = []

    note: Optional[StudentNoteDetail] = None

    # Needed to submit a decision - PATCH .../verdicts/{id}/review takes
    # a verdict id, and until 7.7 no payload the frontend received
    # carried one. None when the student has never been analysed.
    verdict_id: Optional[int] = None

    # The review STANDING BEHIND this verdict's tier, whether it was
    # submitted against this verdict or carried forward from an earlier
    # one. Non-null means a human decided this tier, not the engines,
    # and the card says so rather than letting a carried-forward
    # decision look like an automatic result.
    applied_review_id: Optional[int] = None

    # Every decision ever recorded for this student in this unit at this
    # checkpoint, newest first. Append-only, so this is the full history
    # including any the lecturer later superseded.
    review_history: list[StudentReviewDetail] = []


class StudentReviewSubmit(BaseModel):
    """A lecturer's decision on an engine disagreement."""

    decision: Literal["safe", "low_risk", "high_risk"]
    # Optional on purpose. A lecturer clearing fifteen of these will type
    # "ok" fifteen times if forced, and fifteen instances of "ok" are
    # worse than fifteen blanks - they look like justifications.
    comment: Optional[str] = None


class StudentNoteUpdate(BaseModel):
    """Request body for saving notes. Free text, deliberately."""

    body: str