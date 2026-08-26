"""
Lecturer dashboard aggregation layer - Phase 6.2.

Assembles the single flat payload that drives every chart, KPI tile and
table on the lecturer's analytics dashboard.

THE DUPLICATE-ROW PROBLEM (read this before changing any query here)
--------------------------------------------------------------------
Three of this project's tables are append-only by design:

  * FinalVerdict     - compute_and_stage_final_verdict() always INSERTs.
                       Clicking "Run Analysis" three times leaves three
                       verdict rows for the same student/unit/checkpoint.
  * RiskScore        - same, one new row per engine per run.
  * AssessmentEvent  - immutable on purpose; a correction is a NEW row,
                       never an UPDATE (see the model's docstring).

A naive SELECT would therefore count the same student once per analysis
run and inflate every single chart on the dashboard. Every query below
uses PostgreSQL's DISTINCT ON to collapse each group down to its most
recent row. The rule for DISTINCT ON is that ORDER BY must LEAD with
exactly the DISTINCT ON expressions, then break ties by recency - which
is why each order_by() below looks repetitive. It isn't; it's required.

TENANT ISOLATION
----------------
Everything is anchored to `Unit.lecturer_id == lecturer_id`. A lecturer
can only ever see units they are personally assigned to, and students
are reached exclusively through those units' enrollments. There is no
code path here that can return another lecturer's cohort, and that is
enforced in SQL rather than filtered out in the UI.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment_event import AssessmentEvent
from app.models.criteria import Criteria
from app.models.enrollment import Enrollment
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.unit import Unit
from typing import Optional


# Matches the default used by the risk routes and run-analysis. Kept as a
# named constant so the dashboard and the pipeline can never disagree
# about which checkpoint is "the current one".
DEFAULT_CHECKPOINT_WEEK = 8


def _fetch_units(db: Session, lecturer_id: int) -> list[Unit]:
    """
    Active units assigned to this lecturer, ordered for a stable filter
    dropdown. Archived units are excluded - a lecturer analysing their
    current cohort does not want last year's archived offerings padding
    out their risk distribution.
    """
    stmt = (
        select(Unit)
        .where(Unit.lecturer_id == lecturer_id, Unit.is_active.is_(True))
        .order_by(Unit.year.desc().nullslast(), Unit.unit_code)
    )
    return list(db.execute(stmt).scalars().all())


def _unit_to_dict(unit: Unit, criteria: Optional[list[Criteria]] = None) -> dict:
    """
    One place that decides what a unit looks like over the wire, so the
    dashboard payload and the standalone units list can never describe
    the same unit differently.

    `criteria` is OPTIONAL and defaults to empty on purpose. The whole
    reason GET /lecturer/units exists is that it stays cheap - the units
    page, the unit switcher and the import wizard all want unit codes
    and nothing else. Only get_lecturer_dashboard() passes criteria in,
    because only the students table needs to know how many assessments
    a unit defines in order to render "2 of 3 marked".

    The rows are already loaded by _fetch_criteria_by_unit() for the
    criteria chart, so this adds no extra query.
    """
    return {
        "id": unit.id,
        "unit_code": unit.unit_code,
        "unit_name": unit.unit_name,
        "year": unit.year,
        "teaching_period": unit.teaching_period,
        "level": unit.level,
        "enrolled_count": unit.enrolled_count,
        "criteria": [
            {
                "id": criterion.id,
                "name": criterion.name,
                # .value because category is a CriteriaCategory enum and
                # is nullable on older rows - same guard the student
                # criteria payload uses.
                "category": criterion.category.value if criterion.category else None,
                "threshold": criterion.threshold,
                "max_score": criterion.max_score,
            }
            for criterion in (criteria or [])
        ],
    }


def list_lecturer_units(db: Session, lecturer_id: int) -> list[dict]:
    """
    The lecturer's units on their own, with no cohort data attached.

    Public counterpart to the private _fetch_units helper - used by
    GET /lecturer/units for every screen that needs a unit list without
    paying for the full dashboard payload.
    """
    return [_unit_to_dict(u) for u in _fetch_units(db, lecturer_id)]


def _fetch_enrollments(db: Session, unit_ids: list[int]) -> list[tuple[Student, int]]:
    """
    Every (student, unit_id) pair across the lecturer's units.

    A student enrolled in two of this lecturer's units appears TWICE and
    that is correct: risk is always computed per unit, never globally,
    so the same person can be high risk in one unit and safe in another.
    """
    stmt = (
        select(Student, Enrollment.unit_id)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .where(Enrollment.unit_id.in_(unit_ids))
        .order_by(Student.name, Enrollment.unit_id)
    )
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def _fetch_latest_verdicts(
    db: Session, unit_ids: list[int], checkpoint_week: int
) -> dict[tuple[int, int], FinalVerdict]:
    """
    The single most recent FinalVerdict per (student, unit) at this
    checkpoint, keyed by that pair.

    DISTINCT ON collapses the re-run duplicates described in the module
    docstring. Ties break on id DESC rather than created_at alone,
    because two runs inside the same second would otherwise be ordered
    arbitrarily - id is monotonic and never null, so it is the reliable
    tiebreaker.
    """
    stmt = (
        select(FinalVerdict)
        .where(
            FinalVerdict.unit_id.in_(unit_ids),
            FinalVerdict.checkpoint_week == checkpoint_week,
        )
        .distinct(FinalVerdict.student_id, FinalVerdict.unit_id)
        .order_by(
            # DISTINCT ON keys first - mandatory, not stylistic.
            FinalVerdict.student_id,
            FinalVerdict.unit_id,
            # Then "most recent wins" within each group.
            FinalVerdict.created_at.desc().nullslast(),
            FinalVerdict.id.desc(),
        )
    )
    verdicts = db.execute(stmt).scalars().all()
    return {(v.student_id, v.unit_id): v for v in verdicts}

def _fetch_scores_by_id(db: Session, score_ids: list[int]) -> dict[int, RiskScore]:
    """
    Loads the exact RiskScore rows a verdict was built from.

    Deliberately fetched BY ID off FinalVerdict.rule_score_id /
    ml_score_id rather than by re-querying "latest score for this
    student". Those two can diverge: if a re-run stages fresh engine
    scores but its verdict step then fails for that student, the newest
    scores would belong to no verdict at all. Following the foreign keys
    guarantees the rule tier, ML tier and final tier shown on the
    dashboard all came from the same analysis run and actually agree
    with each other.
    """
    if not score_ids:
        return {}

    stmt = select(RiskScore).where(RiskScore.id.in_(score_ids))
    return {s.id: s for s in db.execute(stmt).scalars().all()}


def _fetch_latest_events(
    db: Session, unit_ids: list[int]
) -> dict[tuple[int, int, int], AssessmentEvent]:
    """
    Each student's current value for each criterion, keyed by
    (student_id, unit_id, criteria_id).

    AssessmentEvent is immutable - a corrected mark is inserted as a new
    row rather than overwriting the old one - so "current value" means
    the latest row by date, exactly as the model's docstring specifies.
    No checkpoint_week filter exists here because raw events aren't
    stamped with one; the checkpoint is a property of the SCORE derived
    from them, not of the underlying data point.
    """
    stmt = (
        select(AssessmentEvent)
        .where(AssessmentEvent.unit_id.in_(unit_ids))
        .distinct(
            AssessmentEvent.student_id,
            AssessmentEvent.unit_id,
            AssessmentEvent.criteria_id,
        )
        .order_by(
            AssessmentEvent.student_id,
            AssessmentEvent.unit_id,
            AssessmentEvent.criteria_id,
            AssessmentEvent.date.desc().nullslast(),
            AssessmentEvent.id.desc(),
        )
    )
    events = db.execute(stmt).scalars().all()
    return {(e.student_id, e.unit_id, e.criteria_id): e for e in events}


def _fetch_criteria_by_unit(db: Session, unit_ids: list[int]) -> dict[int, list[Criteria]]:
    """
    Enabled criteria grouped by unit. Disabled criteria are skipped -
    they no longer contribute to a risk score, so charting them would
    imply they still matter.
    """
    stmt = (
        select(Criteria)
        .where(Criteria.unit_id.in_(unit_ids), Criteria.enabled.is_(True))
        .order_by(Criteria.unit_id, Criteria.id)
    )

    grouped: dict[int, list[Criteria]] = {}
    for criterion in db.execute(stmt).scalars().all():
        grouped.setdefault(criterion.unit_id, []).append(criterion)
    return grouped


def _build_criteria_payload(
    student_id: int,
    unit_id: int,
    unit_criteria: list[Criteria],
    events: dict[tuple[int, int, int], AssessmentEvent],
) -> list[dict]:
    """
    One entry per criterion this student actually has data for.

    A criterion with no matching event is OMITTED, never emitted as
    zero. A missing data point and a genuine score of zero mean very
    different things to a lecturer, and collapsing them would quietly
    drag every cohort average down.
    """
    payload = []

    for criterion in unit_criteria:
        event = events.get((student_id, unit_id, criterion.id))
        if event is None:
            continue

        payload.append(
            {
                "criteria_id": criterion.id,
                "name": criterion.name,
                # .value because category is a CriteriaCategory enum; it
                # is nullable on older rows, hence the guard.
                "category": criterion.category.value if criterion.category else None,
                "score": event.score,
                "threshold": criterion.threshold,
                "max_score": criterion.max_score,
                "trend_value": event.trend_value,
            }
        )

    return payload


def get_lecturer_dashboard(
    db: Session, lecturer_id: int, checkpoint_week: int = DEFAULT_CHECKPOINT_WEEK
) -> dict:
    """
    Builds the complete dashboard payload for one lecturer.

    Runs a fixed number of queries regardless of cohort size (units,
    criteria, enrollments, verdicts, scores, events) - deliberately no
    per-student query, which would turn a 300-student cohort into 300
    round-trips.
    """
    units = _fetch_units(db, lecturer_id)

    # A newly created lecturer with nothing assigned yet is a normal
    # state, not an error - return an empty but well-formed payload so
    # the frontend renders its empty state instead of failing.
    if not units:
        return {"units": [], "students": [], "checkpoint_week": checkpoint_week}

    unit_ids = [u.id for u in units]
    unit_code_by_id = {u.id: u.unit_code for u in units}

    criteria_by_unit = _fetch_criteria_by_unit(db, unit_ids)
    enrollments = _fetch_enrollments(db, unit_ids)
    verdicts = _fetch_latest_verdicts(db, unit_ids, checkpoint_week)
    events = _fetch_latest_events(db, unit_ids)

    # Collect every score id referenced by the verdicts we kept, then
    # load them in ONE query rather than two per student.
    referenced_score_ids: list[int] = []
    for verdict in verdicts.values():
        referenced_score_ids.append(verdict.rule_score_id)
        referenced_score_ids.append(verdict.ml_score_id)
    scores = _fetch_scores_by_id(db, referenced_score_ids)

    students_payload = []

    for student, unit_id in enrollments:
        verdict = verdicts.get((student.id, unit_id))
        rule_score = scores.get(verdict.rule_score_id) if verdict else None
        ml_score = scores.get(verdict.ml_score_id) if verdict else None

        students_payload.append(
            {
                "student_id": student.id,
                "student_number": student.student_number,
                "name": student.name,
                "email": student.email,
                "program": student.program,
                "gender": student.gender,
                "age": student.age,
                "unit_id": unit_id,
                "unit_code": unit_code_by_id[unit_id],
                # No verdict = the pipeline has never successfully run
                # for this student. They stay in the payload so the
                # dashboard can show them as "Not Analysed" rather than
                # silently shrinking the cohort.
                "analysed": verdict is not None,
                "final_tier": verdict.final_tier if verdict else None,
                "requires_review": verdict.requires_review if verdict else False,
                "reason": verdict.reason if verdict else None,
                "checkpoint_week": verdict.checkpoint_week if verdict else None,
                "computed_at": verdict.created_at if verdict else None,
                "rule_tier": rule_score.risk_level if rule_score else None,
                "rule_score": rule_score.risk_score if rule_score else None,
                "ml_tier": ml_score.risk_level if ml_score else None,
                "ml_score": ml_score.risk_score if ml_score else None,
                # Either engine flagging incomplete input is enough to
                # caveat the whole row.
                "is_incomplete": bool(
                    (rule_score and rule_score.is_incomplete)
                    or (ml_score and ml_score.is_incomplete)
                ),
                "criteria": _build_criteria_payload(
                    student.id, unit_id, criteria_by_unit.get(unit_id, []), events
                ),
            }
        )

    return {
        # Same helper GET /lecturer/units uses, so both endpoints always
        # describe a unit identically.
        "units": [_unit_to_dict(u, criteria_by_unit.get(u.id, [])) for u in units],
        "students": students_payload,
        "checkpoint_week": checkpoint_week,
    }