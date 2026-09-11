"""
VerdictReview - a lecturer's manual decision on an engine disagreement
(Phase 7.7).

WHY THIS IS NOT A COLUMN ON FinalVerdict
----------------------------------------
It used to be, and that was a silent data-loss bug. `submit_review_
decision` mutated the verdict row in place, but `compute_and_stage_
final_verdict` always INSERTs a new row and every read in this project
takes the LATEST verdict per (student, unit). So:

    1. Lecturer resolves verdict #12 as safe.
    2. Someone clicks "Run Analysis".
    3. Verdict #47 is inserted with requires_review=True again.
    4. The student is back in the queue and the decision in row #12 is
       unreachable forever.

A review is a judgement about a STUDENT'S SITUATION, not about one row
produced by one run of the engines, so it has to outlive every re-run.

APPEND-ONLY, LIKE EVERY OTHER RECORD OF FACT HERE
--------------------------------------------------
Changing your mind writes a NEW row; nothing is ever mutated. Latest
wins, which is the same rule FinalVerdict, RiskScore and AssessmentEvent
already follow. That makes a misclick fixable while keeping the fact
that it happened - "the lecturer resolved this as high risk, then
changed it to safe an hour later" is exactly the kind of thing an audit
of an early-warning system wants to see, and overwriting would erase it.

THE CARRY-FORWARD KEY: rule_tier AND ml_tier
---------------------------------------------
A review resolves a SPECIFIC disagreement - "the rule engine says safe,
the model says high risk, and I side with safe". Those two tiers are
stored on the row precisely so a later run can ask whether it is looking
at the same disagreement:

  * Both tiers unchanged -> the judgement still applies. The new verdict
    adopts it automatically and the lecturer is not asked again.
  * Either tier moved    -> the situation genuinely changed. The verdict
    returns to the review queue, and the card shows what moved rather
    than silently re-asking.

Storing only the decision, without the tiers it was made about, would
force a choice between re-asking on every run (unusable at 300 students)
and carrying a stale judgement forward onto data the lecturer never saw.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class VerdictReview(Base):
    __tablename__ = "verdict_reviews"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False, index=True)
    checkpoint_week = Column(Integer, nullable=False, default=8)

    # The lecturer's verdict: "safe" | "low_risk" | "high_risk".
    decision = Column(String, nullable=False)

    # Optional. Never required - a lecturer clearing fifteen of these
    # will type "ok" fifteen times if forced, which is worse than
    # nothing because it looks like a justification.
    comment = Column(Text, nullable=True)

    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # The engine pair this decision was made ABOUT. See the module
    # docstring - this is what makes carry-forward safe.
    rule_tier = Column(String, nullable=False)
    ml_tier = Column(String, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), index=True)

    student = relationship("Student")
    unit = relationship("Unit")
    reviewer = relationship("User")