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
    }