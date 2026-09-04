"""
Run Analysis - section E1.

The rule engine, the ML model and the hybrid reconciliation have all
existed since Phase 5. So has an endpoint that runs them
(`/units/{id}/risk/run-analysis`). What has never existed is a way for a
lecturer to press it, and a way for the answer to say anything more
useful than "40 succeeded".

This router adds both: one unit or every unit the lecturer teaches, and
a summary of what actually MOVED rather than what merely ran.

WHY THIS IS NOT JUST A BUTTON ON THE OLD ENDPOINT
-------------------------------------------------
The verdict tables are append-only, so a run destroys nothing and looks
completely safe. It is not quite: it supersedes every current verdict,
and any lecturer review decision whose engine tiers no longer match is
left behind by Phase 7.7's carry-forward rule. A lecturer who re-runs an
analysis can lose a judgement they made last week without a single row
being deleted.

That is worth reporting out loud, which is why the response carries a
diff and not a count.

TENANT ISOLATION
----------------
Anchored on Unit.lecturer_id from the validated JWT. A unit the caller
does not teach returns 404, matching the reports surface. (The older
`/units/{id}/risk/run-analysis` returns 403 for the same case - a
pre-existing inconsistency, noted rather than silently changed here.)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import require_teaching_role
from app.database import get_db
from app.models.enrollment import Enrollment
from app.models.unit import Unit
from app.models.user import User
from app.schemas.analysis import AnalysisRunResult, UnitAnalysisResult
from app.services.ml_engine import MLModelUnavailable, model_is_available
from app.services.analysis_service import (
    run_analysis_for_students,
    snapshot_verdicts,
    summarise_changes,
)

logger = logging.getLogger("eduguard.analysis")

router = APIRouter(
    prefix="/lecturer/analysis",
    tags=["Lecturer - Analysis"],
    dependencies=[Depends(require_teaching_role())],
)


def _default_week() -> int:
    return getattr(settings, "CHECKPOINT_WEEK", 8) or 8


def _owned_units(db: Session, lecturer_id: int, unit_id: Optional[int]) -> list[Unit]:
    """
    The units this run covers. Ownership is resolved in SQL, never
    checked afterwards - a unit_id in a request body is
    attacker-controlled, and this endpoint writes risk scores.
    """
    stmt = select(Unit).where(
        Unit.lecturer_id == lecturer_id, Unit.is_active.is_(True)
    )
    if unit_id is not None:
        stmt = stmt.where(Unit.id == unit_id)
    return list(db.execute(stmt.order_by(Unit.unit_code)).scalars())


def _run_one(db: Session, unit: Unit, checkpoint_week: int) -> dict:
    """
    One unit, with a before-and-after.

    The snapshot MUST be taken before the pipeline stages anything, or
    it reads the rows the run just created and reports that nothing
    changed.
    """
    student_ids = [
        row for row in db.execute(
            select(Enrollment.student_id).where(Enrollment.unit_id == unit.id)
        ).scalars()
    ]

    if not student_ids:
        # Not an error. A unit with no enrolments is a unit nobody has
        # uploaded a cohort for yet, and saying so is more useful than
        # a 400 that reads like the analysis broke.
        return {
            "unit_id": unit.id,
            "unit_code": unit.unit_code,
            "unit_name": unit.unit_name,
            "checkpoint_week": checkpoint_week,
            "total_students": 0,
            "succeeded": 0,
            "failed": 0,
            "skipped_reason": "No students are enrolled in this unit yet.",
            **summarise_changes({}, []),
        }

    before = snapshot_verdicts(db, unit.id, checkpoint_week)
    outcome = run_analysis_for_students(
        db, unit.id, student_ids, checkpoint_week
    )

    return {
        "unit_id": unit.id,
        "unit_code": unit.unit_code,
        "unit_name": unit.unit_name,
        "checkpoint_week": checkpoint_week,
        "total_students": outcome["total_students"],
        "succeeded": outcome["succeeded"],
        "failed": outcome["failed"],
        "skipped_reason": None,
        **summarise_changes(before, outcome["results"]),
    }


@router.post("/run", response_model=AnalysisRunResult)
def run_analysis(
    unit_id: Optional[int] = Query(
        None,
        ge=1,
        description=(
            "Analyse this unit only. Omit to analyse every active unit "
            "the lecturer teaches."
        ),
    ),
    checkpoint_week: Optional[int] = Query(None, ge=1, le=52),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
) -> AnalysisRunResult:
    """
    Recompute rule + ML + hybrid for a unit, or for all of them.

    Uses whatever data is already ingested - no upload required.

    COMMITS PER UNIT, not once at the end. A failure while analysing the
    fourth of six units must not throw away the three that succeeded:
    the pipeline is deterministic, so a partial run is safe to repeat,
    but a lost one is work a lecturer has to notice and redo.
    """
    # Checked ONCE, before anything runs. Without this the pipeline
    # fails per student, 40 times, and reports "40 failed" - which reads
    # as a data problem rather than a missing model file.
    if not model_is_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "The trained risk model is not installed on this server, so "
                "hybrid analysis cannot run. The rule engine is unaffected."
            ),
        )

    week = checkpoint_week or _default_week()
    units = _owned_units(db, current_user.id, unit_id)

    if not units:
        raise HTTPException(
            status_code=404,
            detail=(
                "Unit not found"
                if unit_id is not None
                else "You are not assigned to any active units."
            ),
        )

    unit_results: list[dict] = []
    for unit in units:
        try:
            unit_results.append(_run_one(db, unit, week))
            db.commit()
        except MLModelUnavailable:
            # The model was there at the pre-flight check and has gone
            # since. Rare, but reported as itself rather than folded
            # into a generic failure.
            db.rollback()
            raise HTTPException(
                status_code=503,
                detail="The risk model became unavailable during the run.",
            )
        except Exception:
            db.rollback()
            logger.exception("Analysis failed for unit %s", unit.id)
            unit_results.append({
                "unit_id": unit.id,
                "unit_code": unit.unit_code,
                "unit_name": unit.unit_name,
                "checkpoint_week": week,
                "total_students": 0,
                "succeeded": 0,
                "failed": 0,
                # Reported, not raised. One broken unit must not hide
                # the results of the others in the same run.
                "skipped_reason": "The analysis failed for this unit.",
                **summarise_changes({}, []),
            })

    def total(key: str) -> int:
        return sum(result[key] for result in unit_results)

    return AnalysisRunResult(
        checkpoint_week=week,
        units_analysed=len(unit_results),
        total_students=total("total_students"),
        succeeded=total("succeeded"),
        failed=total("failed"),
        missing_data=total("missing_data"),
        newly_analysed=total("newly_analysed"),
        moved_toward_risk=total("moved_toward_risk"),
        moved_away_from_risk=total("moved_away_from_risk"),
        unchanged=total("unchanged"),
        now_needs_review=total("now_needs_review"),
        review_resolved_by_engines=total("review_resolved_by_engines"),
        lecturer_decisions_carried=total("lecturer_decisions_carried"),
        lecturer_decisions_invalidated=total("lecturer_decisions_invalidated"),
        units=[UnitAnalysisResult(**result) for result in unit_results],
    )


@router.get("/preview", response_model=list[UnitAnalysisResult])
def preview_analysis_scope(
    unit_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teaching_role()),
) -> list[UnitAnalysisResult]:
    """
    What a run WOULD cover, without running anything.

    Feeds the confirmation dialog. A lecturer about to re-score a cohort
    should be told how many students and how many standing review
    decisions are at stake before they press the button, not after.
    """
    week = _default_week()
    units = _owned_units(db, current_user.id, unit_id)

    if not units:
        raise HTTPException(status_code=404, detail="Unit not found")

    out: list[UnitAnalysisResult] = []
    for unit in units:
        enrolled = len(list(db.execute(
            select(Enrollment.student_id).where(Enrollment.unit_id == unit.id)
        ).scalars()))
        existing = snapshot_verdicts(db, unit.id, week)

        out.append(UnitAnalysisResult(
            unit_id=unit.id,
            unit_code=unit.unit_code,
            unit_name=unit.unit_name,
            checkpoint_week=week,
            total_students=enrolled,
            succeeded=0,
            failed=0,
            skipped_reason=(
                "No students are enrolled in this unit yet." if enrolled == 0 else None
            ),
            # Reused to mean "already analysed" here: the field counts
            # students who have a verdict, which is what the dialog needs
            # in order to say whether this is a first run or a re-run.
            unchanged=len(existing),
            lecturer_decisions_carried=sum(
                1 for value in existing.values() if value["review_id"] is not None
            ),
            now_needs_review=sum(
                1 for value in existing.values() if value["requires_review"]
            ),
        ))
    return out