"""
Pydantic schemas for the Run Analysis endpoint (section E1).

WHY THE RESPONSE IS A DIFF, NOT A COUNT
---------------------------------------
The existing pipeline reports `succeeded` and `failed`. That answers
"did it work", not "what did it do", and the second is the question a
lecturer pressing the button actually has. A run that scores 40 students
and moves none of them is a different event from one that moves eleven
into High Risk - and both report "40 succeeded".

The two movement directions are counted separately on purpose. Someone
moving toward risk needs contacting; someone moving away is good news
that needs no action. Summing them into one "changed" figure would lose
exactly the distinction the number exists to make.
"""

from typing import Optional

from pydantic import BaseModel


class TierMovement(BaseModel):
    """One student who ended up in a different tier than they started."""

    student_id: int
    from_tier: Optional[str] = None
    to_tier: Optional[str] = None
    #: "toward_risk" or "away_from_risk".
    direction: str


class UnitAnalysisResult(BaseModel):
    """What one unit's run did."""

    unit_id: int
    unit_code: str
    unit_name: str
    checkpoint_week: int

    total_students: int = 0
    succeeded: int = 0
    failed: int = 0
    missing_data: int = 0
    #: Set when nothing ran, with the reason in plain words. A unit with
    #: no enrolments is not an error - it is a unit nobody has uploaded a
    #: cohort for yet, and saying so beats a 400 that reads like a crash.
    skipped_reason: Optional[str] = None

    newly_analysed: int = 0
    moved_toward_risk: int = 0
    moved_away_from_risk: int = 0
    unchanged: int = 0

    now_needs_review: int = 0
    review_resolved_by_engines: int = 0

    #: Phase 7.7 carries a lecturer's decision forward only while BOTH
    #: engine tiers are unchanged. One that did not carry is a human
    #: judgement this run discarded - reported because nothing was
    #: deleted, so nothing else would tell them.
    lecturer_decisions_carried: int = 0
    lecturer_decisions_invalidated: int = 0

    movements: list[TierMovement] = []


class AnalysisRunResult(BaseModel):
    """The whole run: totals, then a breakdown per unit."""

    checkpoint_week: int
    units_analysed: int

    total_students: int = 0
    succeeded: int = 0
    failed: int = 0
    missing_data: int = 0

    newly_analysed: int = 0
    moved_toward_risk: int = 0
    moved_away_from_risk: int = 0
    unchanged: int = 0

    now_needs_review: int = 0
    review_resolved_by_engines: int = 0
    lecturer_decisions_carried: int = 0
    lecturer_decisions_invalidated: int = 0

    units: list[UnitAnalysisResult] = []