"""
Final Verdict data-wiring layer - Phase 5.2.

Fetches a student's most recent rule_based and ml_model RiskScore rows,
runs them through hybrid_engine.reconcile(), and stages a FinalVerdict
row. Also handles resolving a pending review, once a lecturer submits
their manual decision. Does NOT commit - the calling route owns the
transaction boundary.
"""

from sqlalchemy.orm import Session

from typing import Optional

from app.core.risk_constants import MIN_EVIDENCE_COVERAGE
from app.models.risk_score import RiskScore
from app.models.final_verdicts import FinalVerdict
from app.models.verdict_review import VerdictReview
from app.services.rule_engine import RiskTier
from app.services.hybrid_engine import reconcile


def get_latest_score(db: Session, student_id: int, unit_id: int, source: str, checkpoint_week: int) -> RiskScore | None:
    """Most recent RiskScore row for this student/unit/checkpoint from
    one specific engine (source='rule_based' or 'ml_model')."""
    return (
        db.query(RiskScore)
        .filter(
            RiskScore.student_id == student_id,
            RiskScore.unit_id == unit_id,
            RiskScore.source == source,
            RiskScore.checkpoint_week == checkpoint_week,
        )
        .order_by(RiskScore.computed_at.desc(), RiskScore.id.desc())
        .first()
    )


def build_reason(rule_score: RiskScore, ml_score: RiskScore, requires_review: bool) -> str:
    """Combines both engines' own stored explanations into one final
    reason. If review is required, that's stated up front."""
    combined = f"{rule_score.explanation or ''} {ml_score.explanation or ''}".strip()
    if requires_review:
        return (
            f"Rule engine ({rule_score.risk_level}) and ML model ({ml_score.risk_level}) "
            f"disagree significantly - needs lecturer review. {combined}"
        ).strip()
    return combined


def get_latest_review(
    db: Session, student_id: int, unit_id: int, checkpoint_week: int
) -> Optional[VerdictReview]:
    """
    The most recent review a lecturer recorded for this student, unit and
    checkpoint - regardless of which engine pair it was about.

    verdict_reviews is append-only, so "changed their mind" is a newer
    row rather than an edit, and latest-wins is the same rule every other
    append-only table here follows. Ties break on id DESC as well as
    created_at, because two submissions inside the same second would
    otherwise be ordered arbitrarily.
    """
    return (
        db.query(VerdictReview)
        .filter(
            VerdictReview.student_id == student_id,
            VerdictReview.unit_id == unit_id,
            VerdictReview.checkpoint_week == checkpoint_week,
        )
        .order_by(VerdictReview.created_at.desc(), VerdictReview.id.desc())
        .first()
    )


def review_still_applies(
    review: Optional[VerdictReview], rule_tier: str, ml_tier: str
) -> bool:
    """
    Whether a past decision can be carried onto a fresh verdict.

    A review resolved a SPECIFIC disagreement - "rule says safe, model
    says high risk, and I side with safe". If both engines still say
    exactly that, the lecturer's judgement is about the same situation
    and re-asking them would be pointless noise; at 300 students, one
    "Run Analysis" would reset a queue they had just spent an hour
    clearing.

    If EITHER tier has moved, the disagreement is a different one. The
    old decision was never made about this situation, so carrying it
    forward would put a lecturer's name against a verdict on data they
    have not seen. Those go back in the queue, and the card shows what
    changed instead of silently re-asking.
    """
    if review is None:
        return False
    return review.rule_tier == rule_tier and review.ml_tier == ml_tier


def apply_review_to_verdict(verdict: FinalVerdict, review: VerdictReview) -> None:
    """
    Stamps a lecturer's decision onto a verdict.

    Writes both the FK and the denormalised copy on final_verdicts. The
    copy exists so the risk router's VerdictReviewResult and anything
    reading that table directly keep working; the FK is what lets any
    screen answer "is there a human standing behind this tier" without
    a second query.

    Used for BOTH paths - a decision submitted just now, and one carried
    forward onto a fresh verdict - so the two can never drift into
    setting different fields.
    """
    verdict.final_tier = review.decision
    verdict.requires_review = False
    verdict.reviewed_by = review.reviewed_by
    verdict.review_decision = review.decision
    verdict.reviewed_at = review.created_at
    verdict.review_id = review.id


def compute_and_stage_final_verdict(
    db: Session, student_id: int, unit_id: int, checkpoint_week: int = 8
) -> FinalVerdict:
    """
    Full pipeline: fetch both engines' latest scores -> reconcile ->
    stage a FinalVerdict row. Raises ValueError if either engine hasn't
    scored this student yet - a verdict needs BOTH inputs to exist.

    CARRY-FORWARD (Phase 7.7). When the engines disagree badly enough to
    need a human, this first checks whether a human already decided this
    exact disagreement. If so the decision is applied and the student
    never re-enters the queue. Before this existed, every "Run Analysis"
    silently discarded every review ever made - the verdict row carrying
    the decision was superseded, and every read takes the latest.
    """
    rule_score = get_latest_score(db, student_id, unit_id, "rule_based", checkpoint_week)
    ml_score = get_latest_score(db, student_id, unit_id, "ml_model", checkpoint_week)

    if not rule_score:
        raise ValueError("No rule_based RiskScore found for this student/unit/checkpoint yet")
    if not ml_score:
        raise ValueError("No ml_model RiskScore found for this student/unit/checkpoint yet")

    hybrid_result = reconcile(RiskTier(rule_score.risk_level), RiskTier(ml_score.risk_level))

    verdict = FinalVerdict(
        student_id=student_id,
        unit_id=unit_id,
        checkpoint_week=checkpoint_week,
        rule_score_id=rule_score.id,
        ml_score_id=ml_score.id,
        final_tier=hybrid_result.final_tier.value if hybrid_result.final_tier else None,
        requires_review=hybrid_result.requires_review,
        reason=build_reason(rule_score, ml_score, hybrid_result.requires_review),
    )

    # Only ever applied to a verdict the engines could NOT resolve. A
    # verdict they agreed on is an engine result and must stay one - a
    # stale human decision has no business overriding a fresh consensus.
    if hybrid_result.requires_review:
        review = get_latest_review(db, student_id, unit_id, checkpoint_week)
        if review_still_applies(review, rule_score.risk_level, ml_score.risk_level):
            apply_review_to_verdict(verdict, review)

    db.add(verdict)
    return verdict


def record_review(
    db: Session,
    student_id: int,
    unit_id: int,
    checkpoint_week: int,
    reviewer_id: int,
    decision: str,
    comment: Optional[str],
    verdict: FinalVerdict,
) -> VerdictReview:
    """
    Records a lecturer's decision and applies it to the current verdict.

    APPEND-ONLY. A lecturer changing their mind writes a NEW row; the
    previous decision is never overwritten. That makes a misclick
    fixable - the old code raised outright if reviewed_by was already
    set, so a wrong click was permanent and unfixable from anywhere in
    the app - while keeping the fact that it happened. "Resolved as high
    risk, changed to safe forty minutes later" is exactly what an audit
    of an early-warning system should be able to see.

    The engine tiers are read off the verdict's OWN score rows via the
    foreign keys, never re-queried as "latest score for this student".
    Those two can diverge, and a review stamped with tiers that did not
    produce the disagreement being resolved would carry forward onto the
    wrong future situations.
    """
    rule_score = db.query(RiskScore).filter(RiskScore.id == verdict.rule_score_id).first()
    ml_score = db.query(RiskScore).filter(RiskScore.id == verdict.ml_score_id).first()

    if not rule_score or not ml_score:
        raise ValueError(
            "This verdict's engine scores are missing - it cannot be reviewed"
        )

    review = VerdictReview(
        student_id=student_id,
        unit_id=unit_id,
        checkpoint_week=checkpoint_week,
        decision=decision,
        # Empty strings become NULL: an untouched textarea should not be
        # stored as a justification the lecturer never wrote.
        comment=(comment or "").strip() or None,
        reviewed_by=reviewer_id,
        rule_tier=rule_score.risk_level,
        ml_tier=ml_score.risk_level,
    )
    db.add(review)
    # Needed before apply_review_to_verdict can set the FK - the row has
    # no id until it reaches the database.
    db.flush()

    apply_review_to_verdict(verdict, review)
    return review


def submit_review_decision(
    db: Session,
    verdict_id: int,
    reviewer_id: int,
    decision: str,
    comment: Optional[str] = None,
) -> FinalVerdict:
    """
    Resolves a FinalVerdict with a lecturer's manual decision.

    Kept as the single write path so the older
    PATCH /units/{id}/risk/verdicts/{id}/review endpoint and the newer
    per-student one produce identical state. Two write paths to the same
    fields is how a denormalised copy drifts from its source of truth.

    NO LONGER REFUSES AN ALREADY-REVIEWED VERDICT. Reviews are append-only
    now, so a second decision supersedes the first rather than colliding
    with it.
    """
    verdict = db.query(FinalVerdict).filter(FinalVerdict.id == verdict_id).first()
    if not verdict:
        raise ValueError(f"FinalVerdict {verdict_id} not found")

    # A verdict the engines agreed on has nothing to resolve. Still
    # refused - overriding a fresh consensus is a different feature with
    # different consequences, and silently allowing it here would let the
    # UI drift into offering it.
    if not verdict.requires_review and verdict.review_id is None:
        raise ValueError(
            f"FinalVerdict {verdict_id} did not require review - nothing to resolve"
        )

    record_review(
        db,
        verdict.student_id,
        verdict.unit_id,
        verdict.checkpoint_week,
        reviewer_id,
        decision,
        comment,
        verdict,
    )
    return verdict