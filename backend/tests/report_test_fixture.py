"""
Shared test fixture for the report sections (C1, C2, and later C3/C4).

ONE COHORT, MANY SUITES. C2 asserts things about a rendered PDF that
only mean something if the underlying figures are the ones C1 pinned
down. Building a second fixture for C2 would let the two drift, and a
PDF proved against a cohort with no edge cases proves very little.

Runs against in-memory SQLite. That is the whole reason `report_service`
collapses latest-per-group in Python instead of using PostgreSQL's
DISTINCT ON: a rule only ever exercised on one dialect is a rule that
drifts. Nothing here needs a live database.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
# Importing any model pulls in app.models.__init__, which imports every
# model including EmailMessage - so `create_all` always produces the
# alerts table. The degrade-honestly path is therefore proved by DROPPING
# that table (section 11), which is what an out-of-date migration
# actually looks like in production.
import app.models.student            # noqa: F401
import app.models.unit               # noqa: F401
import app.models.criteria           # noqa: F401
import app.models.enrollment         # noqa: F401
import app.models.final_verdicts     # noqa: F401
import app.models.risk_score         # noqa: F401
import app.models.assessment_event   # noqa: F401
import app.models.verdict_review     # noqa: F401
import app.models.user               # noqa: F401
import app.models.ingestion_batch    # noqa: F401

from app.models.assessment_event import AssessmentEvent
from app.models.criteria import Criteria
from app.models.enrollment import Enrollment
from app.models.enums import UserRole
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.models.email_message import EmailMessage
from app.models.verdict_review import VerdictReview
from app.services.report_service import build_unit_report

NOW = datetime(2026, 8, 26, 10, 0, 0, tzinfo=timezone.utc)
WEEK = 8

# ---------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------

def build_db() -> Session:
    """
    A small but deliberately awkward cohort.

    Every student here exists to trip one specific rule, so a failure
    names the rule rather than "the report is wrong".
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)

    lecturer = User(
        email="l@example.com", full_name="Dr Mine",
        hashed_password="x", role=UserRole.LECTURER, is_active=True,
    )
    other = User(
        email="o@example.com", full_name="Dr Theirs",
        hashed_password="x", role=UserRole.LECTURER, is_active=True,
    )
    db.add_all([lecturer, other])
    db.flush()

    unit = Unit(
        unit_code="ICT101", unit_name="Intro to ICT", year=2026,
        teaching_period="Semester 2", lecturer_id=lecturer.id, is_active=True,
    )
    foreign = Unit(
        unit_code="ICT999", unit_name="Not Mine", year=2026,
        lecturer_id=other.id, is_active=True,
    )
    db.add_all([unit, foreign])
    db.flush()

    # Attendance is a percentage against 50. Moodle is a raw login COUNT
    # against 10. Assessments are raw marks out of max_score. These three
    # scales existing side by side is exactly what the report normalises.
    attendance = Criteria(
        unit_id=unit.id, name="Attendance", weight=0.4, threshold=50.0,
        max_score=100.0, category="attendance", enabled=True,
    )
    tutorial = Criteria(
        unit_id=unit.id, name="Weekly Tutorial", weight=0.2, threshold=60.0,
        max_score=100.0, category="weekly_tut", enabled=True,
    )
    quiz = Criteria(
        unit_id=unit.id, name="Quiz 1", weight=0.2, threshold=45.0,
        max_score=20.0, category="assessment", sequence_number=1, enabled=True,
    )
    essay = Criteria(
        unit_id=unit.id, name="Essay", weight=0.1, threshold=45.0,
        max_score=100.0, category="assessment", sequence_number=2, enabled=True,
    )
    moodle = Criteria(
        unit_id=unit.id, name="Moodle Logins", weight=0.1, threshold=10.0,
        max_score=100.0, category="moodle", enabled=True,
    )
    # No category: scored by the rule engine, invisible to the ML model.
    # Must surface as a caveat, not be folded into a category.
    orphan = Criteria(
        unit_id=unit.id, name="Participation", weight=0.1, threshold=50.0,
        max_score=100.0, category=None, enabled=True,
    )
    # Disabled: must be ignored entirely.
    retired = Criteria(
        unit_id=unit.id, name="Old Test", weight=0.1, threshold=50.0,
        max_score=100.0, category="assessment", enabled=False,
    )
    db.add_all([attendance, tutorial, quiz, essay, moodle, orphan, retired])
    db.flush()

    names = ["Amy High", "Ben Low", "Cara Safe", "Dan Review", "Eve Unscored"]
    students = []
    for index, name in enumerate(names, start=1):
        student = Student(
            student_number=f"S{index:03d}", name=name,
            email=f"s{index}@example.com" if name != "Eve Unscored" else None,
        )
        students.append(student)
    db.add_all(students)
    db.flush()

    for student in students:
        db.add(Enrollment(student_id=student.id, unit_id=unit.id))
    db.flush()

    amy, ben, cara, dan, eve = students

    def event(student, criterion, score, trend=None, when=NOW):
        db.add(AssessmentEvent(
            student_id=student.id, unit_id=unit.id, criteria_id=criterion.id,
            score=score, trend_value=trend, source="manual",
            created_by=lecturer.id, date=when.replace(tzinfo=None),
        ))

    # Amy: failing everything, attendance falling hard.
    event(amy, attendance, 30.0, trend=-25.0)
    event(amy, tutorial, 40.0, trend=-12.0)
    event(amy, quiz, 4.0)          # 4/20 = 20%, NOT 4 against a threshold of 45
    event(amy, essay, 35.0)
    event(amy, moodle, 2.0)

    # Ben: borderline, flat trend.
    event(ben, attendance, 55.0, trend=-2.0)
    event(ben, tutorial, 58.0, trend=0.0)
    event(ben, quiz, 11.0)         # 11/20 = 55%
    event(ben, moodle, 9.0)        # essay deliberately unmarked

    # Cara: comfortable.
    event(cara, attendance, 92.0, trend=4.0)
    event(cara, tutorial, 88.0, trend=1.0)
    event(cara, quiz, 18.0)
    event(cara, essay, 80.0)
    event(cara, moodle, 30.0)

    # Dan: engines disagreed, nobody has decided.
    event(dan, attendance, 60.0, trend=-15.0)
    event(dan, moodle, 6.0)

    # A mark against the DISABLED criterion. It must be invisible: if it
    # leaks in, the assessment sample size and Amy's average both change.
    event(amy, retired, 90.0)

    # An older, superseded attendance row for Amy. If latest-per-group is
    # broken this 99 leaks into the figures and Amy looks fine.
    event(amy, attendance, 99.0, trend=50.0, when=NOW - timedelta(days=30))

    # Eve: enrolled, never analysed, no events at all.

    def score(student, source, value, level, incomplete=False):
        row = RiskScore(
            student_id=student.id, unit_id=unit.id, source=source,
            risk_score=value, risk_level=level, is_incomplete=incomplete,
            checkpoint_week=WEEK, computed_at=NOW.replace(tzinfo=None),
        )
        db.add(row)
        db.flush()
        return row

    def verdict(student, rule, ml, tier, review=False, created=NOW, reviewed_by=None,
                review_id=None):
        row = FinalVerdict(
            student_id=student.id, unit_id=unit.id, checkpoint_week=WEEK,
            rule_score_id=rule.id, ml_score_id=ml.id,
            final_tier=tier, requires_review=review,
            reviewed_by=reviewed_by, review_id=review_id,
            created_at=created.replace(tzinfo=None),
        )
        db.add(row)
        db.flush()
        return row

    verdict(amy, score(amy, "rule", 0.9, "high_risk", incomplete=True),
            score(amy, "ml", 0.88, "high_risk"), "high_risk")
    verdict(ben, score(ben, "rule", 0.5, "low_risk"),
            score(ben, "ml", 0.6, "low_risk"), "low_risk")
    verdict(cara, score(cara, "rule", 0.1, "safe"),
            score(cara, "ml", 0.9, "safe"), "safe")

    # Dan: unresolved disagreement - NULL tier and requires_review.
    verdict(dan, score(dan, "rule", 0.8, "high_risk"),
            score(dan, "ml", 0.7, "safe"), None, review=True)

    # A stale, superseded verdict for Ben. If latest-per-group is broken
    # Ben is counted twice and every percentage is wrong.
    verdict(ben, score(ben, "rule", 0.95, "high_risk"),
            score(ben, "ml", 0.95, "high_risk"), "high_risk",
            created=NOW - timedelta(days=14))

    def alert(student, status, trigger, when):
        db.add(EmailMessage(
            kind="student_alert", student_id=student.id, unit_id=unit.id,
            lecturer_id=lecturer.id, recipient_email=student.email or "x@x",
            subject="Check in", body="...", trigger=trigger, status=status,
            queued_at=when.replace(tzinfo=None),
        ))

    # Amy emailed twice - once automatically, once by hand. Counting
    # alerts as people would claim two students were reached, not one.
    alert(amy, "sent", "automatic", NOW - timedelta(days=7))
    alert(amy, "sent", "manual", NOW)
    alert(ben, "failed", "automatic", NOW - timedelta(days=2))
    alert(ben, "queued", "manual", NOW)
    # A summary to the lecturer, not an alert to a student. Must not be
    # counted as a student having been contacted.
    db.add(EmailMessage(
        kind="lecturer_summary", student_id=None, unit_id=unit.id,
        lecturer_id=lecturer.id, recipient_email="l@example.com",
        subject="Weekly summary", body="...", trigger="automatic",
        status="sent", queued_at=NOW.replace(tzinfo=None),
    ))

    # A resolved review from an earlier disagreement about Cara.
    db.add(VerdictReview(
        student_id=cara.id, unit_id=unit.id, checkpoint_week=WEEK,
        decision="safe", reviewed_by=lecturer.id,
        rule_tier="safe", ml_tier="low_risk",
        created_at=NOW.replace(tzinfo=None),
    ))

    db.commit()
    db.lecturer_id = lecturer.id      # type: ignore[attr-defined]
    db.other_id = other.id            # type: ignore[attr-defined]
    db.unit_id = unit.id              # type: ignore[attr-defined]
    db.foreign_unit_id = foreign.id   # type: ignore[attr-defined]
    return db