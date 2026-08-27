"""
Report aggregation for one unit at one checkpoint (section C1).

WHY THE SERVER DOES THE ARITHMETIC HERE
---------------------------------------
`dashboard_service` deliberately sends raw rows and lets the browser
aggregate, because that dashboard cross-filters six visuals and a
round-trip per filter click would make it feel broken. A report is the
opposite problem: it is fixed, it is computed once, and a copy of it
leaves the building as a PDF. If the browser aggregated it, the PDF
generator would have to aggregate it again - and the two would disagree
the first time either changed.

So this module produces finished numbers, and the screen and the PDF
both render the same object.

PORTABILITY: NO `DISTINCT ON`
-----------------------------
`dashboard_service` collapses append-only tables with PostgreSQL's
DISTINCT ON. That is correct there and untestable here: this module's
rules are exercised against SQLite, and a rule only ever tested on one
dialect is a rule that drifts. Latest-per-group is collapsed in Python
instead, as `alert_service` already does for the same reason. Cohorts
are a few hundred rows; the difference is not measurable.

TENANT ISOLATION
----------------
Anchored on `Unit.lecturer_id` from the validated JWT. A unit the caller
does not teach returns None, which the route renders as 404 - never 403,
which would confirm that someone else's unit exists.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.assessment_event import AssessmentEvent
from app.models.criteria import Criteria
from app.models.enrollment import Enrollment
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.models.verdict_review import VerdictReview

DEFAULT_CHECKPOINT_WEEK = 8

#: Worst first. The report lists at-risk students in this order, so a
#: reader who only gets through the first page has read the students who
#: most need contacting.
BUCKET_ORDER = ["high_risk", "low_risk", "safe", "needs_review", "not_analysed"]

#: MUST match BUCKET_LABELS in the frontend's dashboardAggregations.ts.
#: A report and a dashboard calling the same tier different things is
#: the kind of inconsistency that makes a reader distrust both.
BUCKET_LABELS = {
    "high_risk": "High Risk",
    "low_risk": "Low Risk",
    "safe": "Safe",
    "needs_review": "Needs Review",
    "not_analysed": "Not Analysed",
}

CATEGORY_LABELS = {
    "attendance": "Attendance",
    "weekly_tut": "Weekly Tutorials",
    "assessment": "Assessments",
    "moodle": "Moodle Logins",
}

CATEGORY_ORDER = ["attendance", "weekly_tut", "assessment", "moodle"]

#: Movement smaller than this is noise, not a direction. Same band the
#: dashboard's momentum chart and the students table's trend column use,
#: so the three cannot disagree about who is "declining".
MOMENTUM_BAND_PP = 10

#: Tiers that put a student in the report's at-risk list.
AT_RISK_BUCKETS = ("high_risk", "low_risk", "needs_review")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: Optional[datetime]) -> Optional[datetime]:
    """PostgreSQL columns here are naive; comparisons need a timezone."""
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _round(value: float, places: int = 1) -> float:
    return round(value, places)


# ---------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------

def _owned_unit(db: Session, unit_id: int, lecturer_id: int) -> Optional[Unit]:
    """The unit, only if this lecturer teaches it. Everything else in
    this module hangs off the result."""
    return db.execute(
        select(Unit).where(Unit.id == unit_id, Unit.lecturer_id == lecturer_id)
    ).scalars().first()


def _latest_verdicts(
    db: Session, unit_id: int, checkpoint_week: int
) -> dict[int, FinalVerdict]:
    """Latest verdict per student. Collapsed in Python - see module docstring."""
    rows = db.execute(
        select(FinalVerdict)
        .where(
            FinalVerdict.unit_id == unit_id,
            FinalVerdict.checkpoint_week == checkpoint_week,
        )
        .order_by(FinalVerdict.created_at.desc(), FinalVerdict.id.desc())
    ).scalars().all()

    latest: dict[int, FinalVerdict] = {}
    for verdict in rows:
        latest.setdefault(verdict.student_id, verdict)
    return latest


def _latest_events(
    db: Session, unit_id: int
) -> dict[tuple[int, int], AssessmentEvent]:
    """
    Current value per (student, criterion).

    AssessmentEvent is immutable - a corrected mark is a new row - so
    "current" means the latest by date.
    """
    rows = db.execute(
        select(AssessmentEvent)
        .where(AssessmentEvent.unit_id == unit_id)
        .order_by(AssessmentEvent.date.desc(), AssessmentEvent.id.desc())
    ).scalars().all()

    latest: dict[tuple[int, int], AssessmentEvent] = {}
    for event in rows:
        latest.setdefault((event.student_id, event.criteria_id), event)
    return latest


def _bucket_of(verdict: Optional[FinalVerdict]) -> str:
    """
    Which tier a student is reported in.

    Order matters and mirrors the frontend's getBucket exactly. A
    review-pending verdict deliberately carries a NULL tier, so testing
    final_tier first would report the students who most need a human as
    "not analysed".
    """
    if verdict is None:
        return "not_analysed"
    if verdict.requires_review or verdict.final_tier is None:
        return "needs_review"
    return verdict.final_tier


# ---------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------

def _distribution(buckets: list[str], analysed: int) -> list[dict]:
    """
    Counts per tier.

    The percentage divides by ANALYSED students, not by everyone.
    Including students the engines never scored would quietly understate
    the risk rate, which is the opposite of what an early-warning system
    should do.
    """
    counts = {bucket: 0 for bucket in BUCKET_ORDER}
    for bucket in buckets:
        counts[bucket] = counts.get(bucket, 0) + 1

    return [
        {
            "bucket": bucket,
            "label": BUCKET_LABELS[bucket],
            "count": counts[bucket],
            "percent_of_analysed": (
                _round(counts[bucket] / analysed * 100) if analysed else 0.0
            ),
        }
        for bucket in BUCKET_ORDER
    ]


def _comparable_score(criterion: Criteria, raw: float) -> Optional[float]:
    """
    The score on the same scale as its own threshold.

    THIS IS THE `max_score` BUG'S HOME. An assessment score is a RAW MARK
    (4 out of 20) while its threshold is a PERCENTAGE (45). Comparing 4
    against 45 says a student failed when they may not have, and averaging
    a mark out of 20 with a mark out of 100 produces a number that means
    nothing at all.

    Every other category is already on its own native scale: attendance
    and tutorials are percentages, and Moodle is a login COUNT against a
    count threshold - dividing those by max_score would break them.

    So the normalisation is applied to assessments only, exactly as
    `_student_row` does. Returns None when the mark cannot be placed on a
    scale, which is not the same as a zero.
    """
    if criterion.category is not None and criterion.category.value == "assessment":
        if criterion.max_score is None or criterion.max_score <= 0:
            return None
        return raw / criterion.max_score * 100
    return raw


def _criteria_summary(
    criteria: list[Criteria],
    events: dict[tuple[int, int], AssessmentEvent],
    student_ids: list[int],
) -> list[dict]:
    """
    Cohort performance per category, normalised to "% of threshold".

    WHY NORMALISE. Attendance is a percentage against a threshold of 50;
    Moodle is a raw login COUNT against a threshold of 10. Averaging
    those on one axis would make the Moodle figure meaningless. Dividing
    each student's value by the threshold THEY were held to puts every
    category on one scale where 100% means "exactly at the bar".

    Normalised per student BEFORE averaging, because thresholds are set
    per unit and two units can legitimately differ.

    Assessment marks are additionally divided by their own `max_score`
    first - see `_comparable_score`. Without that step this function
    averages a mark out of 20 with a mark out of 100 and compares the
    result against a percentage.
    """
    buckets: dict[str, dict] = {}

    for criterion in criteria:
        if criterion.category is None:
            # Scored by the rule engine but invisible to the ML model.
            # Reported as a caveat rather than folded into a category it
            # does not belong to.
            continue
        category = criterion.category.value

        for student_id in student_ids:
            event = events.get((student_id, criterion.id))
            if event is None:
                continue
            # A zero or negative threshold makes the ratio meaningless
            # and would produce an Infinity that breaks the axis.
            if criterion.threshold <= 0:
                continue

            # Normalised BEFORE anything is compared or averaged.
            score = _comparable_score(criterion, event.score)
            if score is None:
                continue

            accumulator = buckets.setdefault(
                category,
                {
                    "percent_sum": 0.0,
                    "score_sum": 0.0,
                    "threshold_sum": 0.0,
                    "count": 0,
                    "below": 0,
                    "declining": 0,
                    "has_trend": False,
                },
            )

            accumulator["percent_sum"] += (score / criterion.threshold) * 100
            accumulator["score_sum"] += score
            accumulator["threshold_sum"] += criterion.threshold
            accumulator["count"] += 1
            if score < criterion.threshold:
                accumulator["below"] += 1

            # Only attendance and weekly tutorials carry a trend - the
            # other two are single figures with no early/late window.
            if event.trend_value is not None:
                accumulator["has_trend"] = True
                if event.trend_value <= -MOMENTUM_BAND_PP:
                    accumulator["declining"] += 1

    return [
        {
            "category": category,
            "label": CATEGORY_LABELS.get(category, category),
            "average_score": _round(data["score_sum"] / data["count"]),
            "average_threshold": _round(data["threshold_sum"] / data["count"]),
            "percent_of_threshold": _round(data["percent_sum"] / data["count"]),
            "sample_size": data["count"],
            "below_threshold": data["below"],
            # None, not 0, when the category has no trend concept at all.
            # Zero would read as "nobody is declining"; None reads as
            # "this is not a question we can ask of assessments".
            "declining_count": data["declining"] if data["has_trend"] else None,
        }
        for category in CATEGORY_ORDER
        if (data := buckets.get(category)) is not None
    ]


def _student_row(
    student: Student,
    verdict: Optional[FinalVerdict],
    bucket: str,
    criteria: list[Criteria],
    events: dict[tuple[int, int], AssessmentEvent],
    rule_score: Optional[RiskScore],
    ml_score: Optional[RiskScore],
    reviewer_name: Optional[str],
    alert_count: int,
    last_alert_at: Optional[datetime],
) -> dict:
    """
    One at-risk student with the figures behind their tier.

    Every value is pre-rounded and pre-normalised HERE so the screen and
    the PDF cannot round differently and print two different numbers for
    the same person.
    """
    row = {
        "student_id": student.id,
        "student_number": student.student_number,
        "name": student.name,
        "email": student.email,
        "risk_tier": verdict.final_tier if verdict else None,
        "risk_label": BUCKET_LABELS[bucket],
        "attendance_pct": None,
        "attendance_threshold": None,
        "attendance_trend": None,
        "tutorial_pct": None,
        "tutorial_threshold": None,
        "assessments_marked": 0,
        "assessments_total": 0,
        "assessment_avg_pct": None,
        "moodle_logins": None,
        "moodle_threshold": None,
        "is_incomplete": bool(
            (rule_score and rule_score.is_incomplete)
            or (ml_score and ml_score.is_incomplete)
        ),
        "decided_by_lecturer": bool(verdict and verdict.review_id is not None),
        "reviewer_name": reviewer_name,
        "requires_review": bool(verdict and verdict.requires_review),
        "alerts_sent": alert_count,
        "last_alert_at": last_alert_at,
    }

    assessment_percentages: list[float] = []

    for criterion in criteria:
        if criterion.category is None:
            continue
        category = criterion.category.value
        event = events.get((student.id, criterion.id))

        if category == "attendance":
            row["attendance_threshold"] = _round(criterion.threshold)
            if event is not None and row["attendance_pct"] is None:
                row["attendance_pct"] = _round(event.score)
                row["attendance_trend"] = (
                    _round(event.trend_value) if event.trend_value is not None else None
                )

        elif category == "weekly_tut":
            row["tutorial_threshold"] = _round(criterion.threshold)
            if event is not None and row["tutorial_pct"] is None:
                row["tutorial_pct"] = _round(event.score)

        elif category == "moodle":
            row["moodle_threshold"] = _round(criterion.threshold)
            if event is not None and row["moodle_logins"] is None:
                row["moodle_logins"] = _round(event.score)

        elif category == "assessment":
            row["assessments_total"] += 1
            if event is not None:
                row["assessments_marked"] += 1
                # Same helper the cohort summary uses, so a student's
                # figure and the cohort average can never be normalised
                # differently. See `_comparable_score`.
                percent = _comparable_score(criterion, event.score)
                if percent is not None:
                    assessment_percentages.append(percent)

    if assessment_percentages:
        row["assessment_avg_pct"] = _round(
            sum(assessment_percentages) / len(assessment_percentages)
        )

    return row


def _intervention_summary(
    db: Session, unit_id: int, checkpoint_week: int
) -> tuple[dict, dict[int, tuple[int, Optional[datetime]]]]:
    """
    What the lecturer did: alerts sent, reviews resolved.

    THE ALERTS HALF DEGRADES HONESTLY. Phase 7.8 may not be installed on
    a given deployment, so the table is checked for rather than assumed.
    Returning zeros in that case would read as "nobody was contacted",
    which is a different and much worse claim than "this feature is not
    installed" - so `available` says which it is.

    Also returns per-student alert counts, so the at-risk list can show
    who has already been contacted without a second pass over the table.
    """
    summary = {
        "available": False,
        "alerts_total": 0,
        "alerts_sent": 0,
        "alerts_failed": 0,
        "alerts_queued": 0,
        "alerts_automatic": 0,
        "alerts_manual": 0,
        "students_contacted": 0,
        "reviews_resolved": 0,
        "reviews_pending": 0,
    }
    per_student: dict[int, tuple[int, Optional[datetime]]] = {}

    # Reviews are part of 7.7, which is a hard dependency of this
    # module, so they are counted unconditionally.
    reviews = db.execute(
        select(VerdictReview).where(
            VerdictReview.unit_id == unit_id,
            VerdictReview.checkpoint_week == checkpoint_week,
        )
    ).scalars().all()
    # Distinct students, not rows: reviews are append-only, so a lecturer
    # who changed their mind leaves two rows for one decision.
    summary["reviews_resolved"] = len({review.student_id for review in reviews})

    if db.bind is not None and inspect(db.bind).has_table("email_messages"):
        from app.models.email_message import EmailMessage  # local: optional feature

        summary["available"] = True

        messages = db.execute(
            select(EmailMessage).where(
                EmailMessage.kind == "student_alert",
                EmailMessage.unit_id == unit_id,
            )
        ).scalars().all()

        contacted: set[int] = set()
        for message in messages:
            summary["alerts_total"] += 1
            if message.status == "sent":
                summary["alerts_sent"] += 1
            elif message.status == "failed":
                summary["alerts_failed"] += 1
            else:
                summary["alerts_queued"] += 1

            if message.trigger == "automatic":
                summary["alerts_automatic"] += 1
            else:
                summary["alerts_manual"] += 1

            if message.student_id is not None:
                contacted.add(message.student_id)
                count, latest = per_student.get(message.student_id, (0, None))
                queued_at = _as_aware(message.queued_at)
                if latest is None or (queued_at and queued_at > latest):
                    latest = queued_at
                per_student[message.student_id] = (count + 1, latest)

        summary["students_contacted"] = len(contacted)

    return summary, per_student


def _caveats(
    criteria: list[Criteria],
    buckets: list[str],
    incomplete_count: int,
    last_analysed_at: Optional[datetime],
    intervention_available: bool,
    now: datetime,
) -> list[str]:
    """
    The qualifications this document must carry.

    Computed server-side and rendered in BOTH the screen and the PDF.
    Every other view in this project qualifies itself through tooltips,
    amber icons and badges; a PDF has none of those and gets forwarded to
    a course coordinator with no context at all. This list is the
    mechanism that stops a document claiming more certainty than the
    system has.
    """
    caveats: list[str] = []

    needs_review = buckets.count("needs_review")
    if needs_review:
        caveats.append(
            f"{needs_review} student{'s' if needs_review != 1 else ''} "
            f"{'have' if needs_review != 1 else 'has'} no risk tier: the rule engine "
            "and the ML model disagreed and the disagreement has not been resolved."
        )

    not_analysed = buckets.count("not_analysed")
    if not_analysed:
        caveats.append(
            f"{not_analysed} enrolled student{'s' if not_analysed != 1 else ''} "
            f"{'have' if not_analysed != 1 else 'has'} never been analysed and "
            "{} not counted in any percentage above.".format(
                "are" if not_analysed != 1 else "is"
            )
        )

    if incomplete_count:
        caveats.append(
            f"{incomplete_count} risk score{'s' if incomplete_count != 1 else ''} "
            f"{'were' if incomplete_count != 1 else 'was'} computed on incomplete "
            "input data and should not be read with full confidence."
        )

    uncategorised = [c for c in criteria if c.category is None]
    if uncategorised:
        names = ", ".join(c.name for c in uncategorised)
        caveats.append(
            f"{len(uncategorised)} criterion/criteria on this unit have no category "
            f"set ({names}). These are scored by the rule engine but are invisible to "
            "the ML model, which can manufacture disagreement between the two."
        )

    if last_analysed_at is not None:
        age_days = (now - last_analysed_at).days
        if age_days >= 7:
            caveats.append(
                f"The analysis behind this report ran {age_days} days ago. Figures "
                "reflect the data as it stood then, not today."
            )
    else:
        caveats.append(
            "No analysis has been run for this unit at this checkpoint, so no risk "
            "tiers exist."
        )

    if not intervention_available:
        caveats.append(
            "The alerts feature is not installed on this deployment, so the "
            "intervention record below counts resolved reviews only. It is not "
            "evidence that no students were contacted."
        )

    return caveats


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

def build_unit_report(
    db: Session,
    lecturer_id: int,
    unit_id: int,
    checkpoint_week: int = DEFAULT_CHECKPOINT_WEEK,
    now: Optional[datetime] = None,
) -> Optional[dict]:
    """
    The whole report for one unit, or None if the caller does not teach it.

    Runs a fixed number of queries regardless of cohort size - no
    per-student query, which would turn a 300-student unit into 300
    round-trips for a document nobody reads that closely.
    """
    now = now or _now()

    unit = _owned_unit(db, unit_id, lecturer_id)
    if unit is None:
        return None

    lecturer = db.get(User, unit.lecturer_id) if unit.lecturer_id else None

    criteria = list(
        db.execute(
            select(Criteria)
            .where(Criteria.unit_id == unit_id, Criteria.enabled.is_(True))
            .order_by(Criteria.id)
        ).scalars()
    )

    students = list(
        db.execute(
            select(Student)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .where(Enrollment.unit_id == unit_id)
            .order_by(Student.name)
        ).scalars()
    )
    student_ids = [student.id for student in students]

    verdicts = _latest_verdicts(db, unit_id, checkpoint_week)
    events = _latest_events(db, unit_id)

    # Engine scores loaded BY FOREIGN KEY off the verdict, never by
    # "latest score for this student". If a re-run staged fresh scores
    # but its verdict step failed, the newest scores belong to no verdict
    # - following the FKs guarantees the tiers reported came from one run.
    score_ids: list[int] = []
    for verdict in verdicts.values():
        score_ids += [verdict.rule_score_id, verdict.ml_score_id]
    scores = (
        {
            score.id: score
            for score in db.execute(
                select(RiskScore).where(RiskScore.id.in_(score_ids))
            ).scalars()
        }
        if score_ids
        else {}
    )

    reviewer_names = {
        user.id: user.full_name
        for user in db.execute(select(User)).scalars()
    }

    intervention, alerts_per_student = _intervention_summary(
        db, unit_id, checkpoint_week
    )

    buckets: list[str] = []
    at_risk: list[dict] = []
    incomplete_count = 0
    last_analysed_at: Optional[datetime] = None
    pending_reviews = 0

    for student in students:
        verdict = verdicts.get(student.id)
        bucket = _bucket_of(verdict)
        buckets.append(bucket)

        rule_score = scores.get(verdict.rule_score_id) if verdict else None
        ml_score = scores.get(verdict.ml_score_id) if verdict else None

        if (rule_score and rule_score.is_incomplete) or (
            ml_score and ml_score.is_incomplete
        ):
            incomplete_count += 1

        if verdict is not None:
            computed = _as_aware(verdict.created_at)
            if computed and (last_analysed_at is None or computed > last_analysed_at):
                last_analysed_at = computed
            if verdict.requires_review:
                pending_reviews += 1

        if bucket in AT_RISK_BUCKETS:
            count, latest = alerts_per_student.get(student.id, (0, None))
            at_risk.append(
                _student_row(
                    student, verdict, bucket, criteria, events,
                    rule_score, ml_score,
                    reviewer_names.get(verdict.reviewed_by) if verdict else None,
                    count, latest,
                )
            )

    intervention["reviews_pending"] = pending_reviews

    # Worst first, then alphabetical. A reader who only gets through the
    # first page has read the students who most need contacting.
    severity = {bucket: index for index, bucket in enumerate(BUCKET_ORDER)}
    at_risk.sort(
        key=lambda row: (
            severity.get(row["risk_tier"] or "needs_review", 99),
            row["name"],
        )
    )

    analysed = len(students) - buckets.count("not_analysed")

    return {
        "unit_id": unit.id,
        "unit_code": unit.unit_code,
        "unit_name": unit.unit_name,
        "year": unit.year,
        "teaching_period": unit.teaching_period,
        "lecturer_name": lecturer.full_name if lecturer else None,
        "checkpoint_week": checkpoint_week,
        "generated_at": now,
        "enrolled_count": len(students),
        "analysed_count": analysed,
        "not_analysed_count": buckets.count("not_analysed"),
        "last_analysed_at": last_analysed_at,
        "distribution": _distribution(buckets, analysed),
        "criteria": _criteria_summary(criteria, events, student_ids),
        "at_risk": at_risk,
        "intervention": intervention,
        "caveats": _caveats(
            criteria, buckets, incomplete_count, last_analysed_at,
            intervention["available"], now,
        ),
    }


def available_checkpoints(
    db: Session, lecturer_id: int, unit_id: int
) -> Optional[list[dict]]:
    """
    Which checkpoint weeks this unit actually has an analysis for.

    Feeds the week selector. Building that selector from a fixed 1-14
    range would offer a lecturer thirteen weeks that all render "no
    analysis has been run" - a menu of dead ends.

    Returns None when the caller does not teach the unit, which the
    route renders as 404, exactly as the report itself does. Ownership
    is re-checked here rather than trusted from a previous call: this is
    a separate request and the unit id in it is attacker-controlled.

    Counts DISTINCT STUDENTS, not verdict rows. `final_verdicts` is
    append-only, so a unit re-analysed four times would otherwise report
    four times its cohort size.
    """
    if _owned_unit(db, unit_id, lecturer_id) is None:
        return None

    rows = db.execute(
        select(FinalVerdict).where(FinalVerdict.unit_id == unit_id)
    ).scalars().all()

    weeks: dict[int, dict] = {}
    for verdict in rows:
        entry = weeks.setdefault(
            verdict.checkpoint_week,
            {"week": verdict.checkpoint_week, "students": set(),
             "last_analysed_at": None},
        )
        entry["students"].add(verdict.student_id)
        computed = _as_aware(verdict.created_at)
        if computed and (
            entry["last_analysed_at"] is None
            or computed > entry["last_analysed_at"]
        ):
            entry["last_analysed_at"] = computed

    return [
        {
            "week": entry["week"],
            "student_count": len(entry["students"]),
            "last_analysed_at": entry["last_analysed_at"],
        }
        for entry in sorted(weeks.values(), key=lambda e: e["week"])
    ]