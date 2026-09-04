"""
Analysis orchestration - Phase 5.2 completion.

Runs the full rule -> ML -> final verdict pipeline for one or many
students in a unit. Used both automatically after ingestion (bulk or
manual) and on-demand via the "Run Analysis" endpoint.

Each student is processed independently: if one student's pipeline
fails (bad data, edge case), that failure is recorded and processing
continues for everyone else. This is safe without needing savepoints -
every exception in the underlying rule/ML/verdict service functions
surfaces BEFORE db.add() is called, so a failed student never leaves
anything partially staged in the session for other students to trip over.

db.flush() is called explicitly between each engine's stage - the
final verdict step queries for the rule/ML RiskScore rows staged just
before it, and flush() guarantees those are visible to that query
regardless of whether this session's autoflush setting is on or off,
rather than relying on an assumption about session configuration.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.services.rule_score_service import compute_and_stage_rule_score
from app.services.ml_score_service import compute_and_stage_ml_score
from app.services.final_verdict_service import compute_and_stage_final_verdict


def run_analysis_for_student(
    db: Session, student_id: int, unit_id: int, checkpoint_week: int = 8
) -> dict:
    """
    Runs rule engine -> ML engine -> hybrid reconciliation for ONE
    student, in that order. Explicit flush() after each of the first
    two stages guarantees the final verdict step's queries can see them.
    """
    rule_score = compute_and_stage_rule_score(db, student_id, unit_id, checkpoint_week)
    db.flush()

    ml_score = compute_and_stage_ml_score(db, student_id, unit_id, checkpoint_week)
    db.flush()

    verdict = compute_and_stage_final_verdict(db, student_id, unit_id, checkpoint_week)

    return {
        "student_id": student_id,
        "rule_level": rule_score.risk_level,
        "ml_level": ml_score.risk_level,
        "final_tier": verdict.final_tier,
        "requires_review": verdict.requires_review,
        "is_missing_data": verdict.is_missing_data,
    }


def run_analysis_for_students(
    db: Session, unit_id: int, student_ids: list[int], checkpoint_week: int = 8
) -> dict:
    """
    Runs the full pipeline for each student_id given, isolating failures
    per-student. Does NOT commit - the calling route commits once at the
    end. Whatever succeeded gets committed; failures are simply never
    staged and are reported back separately, not rolled back.
    """
    results = []
    errors = []

    for student_id in student_ids:
        try:
            result = run_analysis_for_student(db, student_id, unit_id, checkpoint_week)
            results.append(result)
        except Exception as e:
            errors.append({"student_id": student_id, "reason": str(e)})

    return {
        "total_students": len(student_ids),
        "succeeded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
        "missing_data": sum(1 for result in results if result["is_missing_data"]),
    }


# ---------------------------------------------------------------------
# "What changed" - section E1
# ---------------------------------------------------------------------
#
# WHY A DIFF AND NOT JUST A COUNT.
#
# `run_analysis_for_students` reports how many students the pipeline
# succeeded on. That answers "did it work", not "what did it do" - and
# the second question is the one a lecturer pressing the button actually
# has. A run that scores 40 students and moves none of them is a
# completely different event from one that moves eleven into High Risk,
# and both currently report "40 succeeded".
#
# It matters more than usual here because the verdict tables are
# APPEND-ONLY. A run never overwrites anything, so nothing looks
# destructive - but it does supersede every current verdict, and any
# lecturer review decision whose engine tiers no longer match is
# silently left behind (Phase 7.7's carry-forward rule). That is worth
# reporting out loud rather than leaving someone to notice their Needs
# Review queue changed.

#: Worse first. Used only to decide whether a student moved toward or
#: away from risk; `None` (an unresolved engine disagreement) is not on
#: this scale and is counted separately.
_TIER_SEVERITY = {"high_risk": 0, "low_risk": 1, "safe": 2}


def snapshot_verdicts(
    db: Session, unit_id: int, checkpoint_week: int
) -> dict[int, dict]:
    """
    The state of play BEFORE a run, as {student_id: {...}}.

    Collapses the append-only table to the latest row per student in
    Python rather than with DISTINCT ON, so this stays testable on
    SQLite - the same reason `report_service` does it that way.

    Must be called before the pipeline stages anything, or it will read
    the rows the run just created and report that nothing changed.
    """
    from app.models.final_verdicts import FinalVerdict

    rows = db.execute(
        select(FinalVerdict)
        .where(
            FinalVerdict.unit_id == unit_id,
            FinalVerdict.checkpoint_week == checkpoint_week,
        )
        .order_by(FinalVerdict.created_at.desc(), FinalVerdict.id.desc())
    ).scalars().all()

    latest: dict[int, dict] = {}
    for verdict in rows:
        latest.setdefault(verdict.student_id, {
            "final_tier": verdict.final_tier,
            "requires_review": bool(verdict.requires_review),
            "review_id": verdict.review_id,
        })
    return latest


def summarise_changes(before: dict[int, dict], results: list[dict]) -> dict:
    """
    Turns a before-snapshot and the run's per-student results into the
    sentence a lecturer needs.

    Movement is reported in two directions and they are NOT symmetric in
    meaning. Someone moving toward risk needs contacting; someone moving
    away is good news but does not need an action. They are counted
    separately so the UI can lead with the first.
    """
    summary = {
        "newly_analysed": 0,
        "moved_toward_risk": 0,
        "moved_away_from_risk": 0,
        "unchanged": 0,
        "now_needs_review": 0,
        "review_resolved_by_engines": 0,
        "lecturer_decisions_carried": 0,
        "lecturer_decisions_invalidated": 0,
        "missing_data": 0,
        "movements": [],
    }

    for result in results:
        student_id = result["student_id"]
        summary["missing_data"] += int(bool(result.get("is_missing_data")))
        after_tier = result.get("final_tier")
        after_review = bool(result.get("requires_review"))
        prior = before.get(student_id)

        if prior is None:
            summary["newly_analysed"] += 1
            if after_review:
                summary["now_needs_review"] += 1
            continue

        before_tier = prior["final_tier"]
        before_review = prior["requires_review"]

        # A student who has entered or left the "engines disagreed"
        # state has not moved along the risk scale - they have moved on
        # and off it, which is a different event.
        if after_review and not before_review:
            summary["now_needs_review"] += 1
        elif before_review and not after_review:
            summary["review_resolved_by_engines"] += 1

        # Phase 7.7: a lecturer's decision carries forward ONLY while
        # both engine tiers are unchanged. One that did not carry is a
        # human judgement the run has just discarded.
        if prior["review_id"] is not None:
            # `result` carries no review_id, so infer from the outcome:
            # a decided verdict is neither pending nor tier-less.
            if after_review or after_tier is None:
                summary["lecturer_decisions_invalidated"] += 1
            else:
                summary["lecturer_decisions_carried"] += 1

        if before_tier == after_tier:
            summary["unchanged"] += 1
            continue

        before_rank = _TIER_SEVERITY.get(before_tier)
        after_rank = _TIER_SEVERITY.get(after_tier)
        if before_rank is None or after_rank is None:
            # One side is an unresolved disagreement. Already counted
            # above; not a movement along the scale.
            continue

        direction = "toward_risk" if after_rank < before_rank else "away_from_risk"
        summary[f"moved_{direction}"] += 1
        summary["movements"].append({
            "student_id": student_id,
            "from_tier": before_tier,
            "to_tier": after_tier,
            "direction": direction,
        })

    # Worst destinations first, so a truncated list still shows the
    # students who most need contacting.
    summary["movements"].sort(
        key=lambda m: (_TIER_SEVERITY.get(m["to_tier"], 9), m["student_id"])
    )
    return summary