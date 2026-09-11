"""
Section B1 verification - evidence coverage.

THE BUG THIS SUITE EXISTS TO PREVENT COMING BACK.

Mei Fujita (student 20008) attended 6 of 7 classes, submitted nearly
every tutorial, and had NO mark for either assessment - 65% of her
unit's weight simply did not exist. Both engines reported her as a
low-risk student and the final verdict agreed, because:

  * the rule engine divided her score by the weight it had rather than
    the weight that applied, so 3 small criteria out of 5 produced a
    confident number;
  * the ML scorer imputed the missing assessment average and then
    failed to flag the imputation, because it searched note strings for
    a phrase the assessment note did not contain;
  * the final verdict had nothing to consult about how much evidence
    either score rested on.

A missing mark is not a passing mark. The fix does not invent a new
tier - it routes thin-evidence students into the review queue that
already exists, so a human decides. These checks pin that behaviour at
all three layers, and pin the two boundaries either side of the floor.
"""

import sys
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import configure_mappers, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registers every mapper
from app.models.base import Base
from app.models.assessment_event import AssessmentEvent
from app.models.criteria import Criteria
from app.models.enrollment import Enrollment
from app.models.enums import CriteriaCategory, UserRole
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User

from app.core.risk_constants import MIN_EVIDENCE_COVERAGE
from app.services.final_verdict_service import (
    compute_and_stage_final_verdict,
    describe_coverage,
    insufficient_evidence,
)
from app.services.ml_score_service import (
    compute_and_stage_ml_score,
    missing_feature_keys,
    structural_feature_keys,
)
from app.services.rule_engine import compute_rule_based_risk
from app.services.rule_score_service import compute_and_stage_rule_score

failures: list[str] = []
section = 0
WEEK = 8


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"    PASS  {label}")
    else:
        print(f"    FAIL  {label}  {detail}")
        failures.append(label)


def heading(title: str) -> None:
    global section
    section += 1
    print(f"\n[{section}] {title}")


# ---------------------------------------------------------------------
# Fixture
#
# One in-memory database, one unit, one student per scenario. The unit's
# weights are the real ones from Mei's trimester, so the coverage
# fractions below are the fractions the live system computes rather than
# round numbers chosen to make the assertions pass.
#
#   attendance 0.50 | moodle 0.05 | weekly tut 0.10
#   assessment 1 0.20 (max 20) | assessment 2 0.45 (max 45)
#   total applicable weight = 1.30
# ---------------------------------------------------------------------

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
configure_mappers()
Base.metadata.create_all(engine)
db = sessionmaker(bind=engine)()

lecturer = User(
    email="coverage@example.com", full_name="Bo Lecturer",
    role=UserRole.LECTURER, hashed_password="x", is_active=True,
)
db.add(lecturer)
db.commit()

unit = Unit(
    unit_code="ICT730", unit_name="Systems", year=2026, teaching_period="T2",
    level="master", start_date=date(2026, 2, 23), lecturer_id=lecturer.id,
    is_active=True, status="ASSIGNED", class_code="LA1",
)
db.add(unit)
db.commit()


def make_criterion(name, category, weight, max_score, threshold, sequence):
    criterion = Criteria(
        unit_id=unit.id, name=name, category=category.value, weight=weight,
        max_score=max_score, threshold=threshold, enabled=True,
        sequence_number=sequence,
    )
    db.add(criterion)
    db.commit()
    return criterion


ATTENDANCE = make_criterion("Attendance", CriteriaCategory.ATTENDANCE, 0.50, 100.0, 50.0, 1)
MOODLE = make_criterion("Moodle", CriteriaCategory.MOODLE, 0.05, 100.0, 10.0, 1)
TUTORIAL = make_criterion("Weekly tuts", CriteriaCategory.WEEKLY_TUT, 0.10, 100.0, 50.0, 1)
ASSESSMENT_1 = make_criterion("Assessment 1", CriteriaCategory.ASSESSMENT, 0.20, 20.0, 50.0, 1)
ASSESSMENT_2 = make_criterion("Assessment 2", CriteriaCategory.ASSESSMENT, 0.45, 45.0, 50.0, 2)

ALL_CRITERIA = [ATTENDANCE, MOODLE, TUTORIAL, ASSESSMENT_1, ASSESSMENT_2]
TOTAL_WEIGHT = sum(criterion.weight for criterion in ALL_CRITERIA)  # 1.30


def make_student(number: str, name: str) -> Student:
    student = Student(student_number=number, name=name, email=f"{number}@example.com")
    db.add(student)
    db.commit()
    db.add(Enrollment(student_id=student.id, unit_id=unit.id))
    db.commit()
    return student


def add_event(student: Student, criterion: Criteria, score: float, trend=None) -> None:
    db.add(AssessmentEvent(
        student_id=student.id, unit_id=unit.id, criteria_id=criterion.id,
        score=score, trend_value=trend, date=date(2026, 4, 20),
        source="manual", created_by=lecturer.id,
    ))
    db.commit()


# Mei: everything present EXCEPT the two assessments.
mei = make_student("20008", "Mei Fujita")
add_event(mei, ATTENDANCE, 85.71, 0.0)
add_event(mei, MOODLE, 16.0)
add_event(mei, TUTORIAL, 92.86, 0.0)

# Nearly complete: only the Moodle datum is absent - 0.05 of 1.30.
nearly = make_student("20009", "Ana Complete")
add_event(nearly, ATTENDANCE, 91.0, 0.0)
add_event(nearly, TUTORIAL, 88.0, 0.0)
add_event(nearly, ASSESSMENT_1, 15.0)
add_event(nearly, ASSESSMENT_2, 34.0)

# Every criterion scored.
whole = make_student("20010", "Sam Whole")
add_event(whole, ATTENDANCE, 91.0, 0.0)
add_event(whole, MOODLE, 40.0)
add_event(whole, TUTORIAL, 88.0, 0.0)
add_event(whole, ASSESSMENT_1, 15.0)
add_event(whole, ASSESSMENT_2, 34.0)

# Enrolled and nothing else. The row exists; no mark ever arrived.
empty = make_student("20011", "Ken Nodata")


# ---------------------------------------------------------------------
# 1. The rule engine measures the weight that APPLIES, not the weight it
#    happened to find.
# ---------------------------------------------------------------------

heading("Rule engine coverage is scored weight over applicable weight")

mei_rule = compute_and_stage_rule_score(db, mei.id, unit.id, WEEK)
db.commit()

expected_mei_coverage = (0.50 + 0.05 + 0.10) / TOTAL_WEIGHT  # 0.5000
check(
    "Mei's rule coverage is 50%, not 100%",
    abs((mei_rule.coverage or 0.0) - expected_mei_coverage) < 0.001,
    f"got {mei_rule.coverage}",
)
check(
    "Mei's rule coverage sits below the floor",
    (mei_rule.coverage or 0.0) < MIN_EVIDENCE_COVERAGE,
    f"{mei_rule.coverage} vs floor {MIN_EVIDENCE_COVERAGE}",
)

whole_rule = compute_and_stage_rule_score(db, whole.id, unit.id, WEEK)
db.commit()
check(
    "A fully marked student reaches 100% coverage",
    abs((whole_rule.coverage or 0.0) - 1.0) < 0.001,
    f"got {whole_rule.coverage}",
)

empty_rule = compute_and_stage_rule_score(db, empty.id, unit.id, WEEK)
db.commit()
check(
    "A student with no marks at all reaches 0% coverage",
    abs((empty_rule.coverage or 0.0) - 0.0) < 0.001,
    f"got {empty_rule.coverage}",
)


# ---------------------------------------------------------------------
# 2. The floor is a judgement, and both sides of it are pinned.
#
# A floor nobody tests is a number that drifts. These two checks are the
# whole argument for 0.70 written as code: a student missing only their
# Moodle count keeps a tier, a student missing a major assessment does
# not.
# ---------------------------------------------------------------------

heading("The floor separates a missing Moodle count from a missing assessment")

nearly_rule = compute_and_stage_rule_score(db, nearly.id, unit.id, WEEK)
db.commit()

check(
    "Missing only Moodle leaves coverage above the floor",
    (nearly_rule.coverage or 0.0) >= MIN_EVIDENCE_COVERAGE,
    f"{nearly_rule.coverage} vs floor {MIN_EVIDENCE_COVERAGE}",
)
check(
    "That student is still measurably short of complete",
    (nearly_rule.coverage or 0.0) < 1.0,
    f"got {nearly_rule.coverage}",
)


# ---------------------------------------------------------------------
# 3. The rule engine's own dataclass, tested directly.
#
# Going through the service proves the wiring; going through the engine
# proves the arithmetic, including the zero-weight case that would
# otherwise divide by zero.
# ---------------------------------------------------------------------

heading("Coverage arithmetic on the engine result itself")

no_criteria = compute_rule_based_risk([])
check(
    "A unit with no criteria reports 0 coverage rather than raising",
    no_criteria.coverage == 0.0,
    f"got {no_criteria.coverage}",
)
check(
    "...and is not treated as having enough evidence",
    no_criteria.has_enough_evidence is False,
)


# ---------------------------------------------------------------------
# 4. The ML scorer flags an imputed feature by KEY, not by string search.
#
# The original defect: `"no data yet" in note` never matched the
# assessment note, so an imputed assessment average was reported as a
# real one. Comparing feature keys cannot silently stop matching when
# somebody rewords a sentence.
# ---------------------------------------------------------------------

heading("Missing model inputs are identified structurally")

check(
    "A None-valued feature is reported missing",
    missing_feature_keys({"a": None, "b": 1.0}) == ["a"],
)
check(
    "A feature with a value is not",
    missing_feature_keys({"b": 1.0}) == [],
)
check(
    "A structurally absent criterion is parsed out of its note",
    structural_feature_keys(
        ["tut_completion_pct / tut_trend (structurally absent: unit has no tutorials)"]
    ) == {"tut_completion_pct", "tut_trend"},
    f"got {structural_feature_keys(['tut_completion_pct / tut_trend (structurally absent: unit has no tutorials)'])}",
)
check(
    "A note that is not about absence contributes nothing",
    structural_feature_keys(["moodle_login_count imputed from cohort median"]) == set(),
)

# The live scorer needs the trained artifact. Where it is unavailable
# the suite says so rather than reporting a pass it did not earn - a
# skipped check that prints as a pass is worse than no check.
try:
    mei_ml = compute_and_stage_ml_score(db, mei.id, unit.id, WEEK)
    db.commit()
    ml_available = mei_ml is not None and mei_ml.risk_score is not None
except Exception as error:  # noqa: BLE001 - the artifact is gitignored on some checkouts
    print(f"    SKIP  live ML scorer unavailable ({type(error).__name__}: {error})")
    mei_ml = None
    ml_available = False

if ml_available:
    check(
        "Mei's ML score is flagged incomplete",
        mei_ml.is_incomplete is True,
    )
    check(
        "...and names the assessment feature it had to impute",
        "assessment_avg_pct" in (mei_ml.missing_criteria or ""),
        f"got {mei_ml.missing_criteria!r}",
    )
    # THE CHECK THAT CAUGHT THE SECOND BUG. Feature-count coverage put
    # Mei at 83% here while the rule engine put her at 50%, so the ML
    # half of the gate abstained on the record it exists for. Both
    # engines now measure share of unit weight.
    check(
        "...and its coverage matches the rule engine's, not a feature count",
        abs((mei_ml.coverage or 0.0) - expected_mei_coverage) < 0.001,
        f"got {mei_ml.coverage}, rule engine says {expected_mei_coverage}",
    )
    check(
        "...which puts it below the floor on its own",
        (mei_ml.coverage or 0.0) < MIN_EVIDENCE_COVERAGE,
        f"got {mei_ml.coverage}",
    )


# ---------------------------------------------------------------------
# 5. The gate. NULL coverage must leave history alone.
#
# Every verdict written before this feature existed has coverage NULL.
# Reading NULL as "insufficient" would move an entire historical cohort
# into the review queue on the morning this shipped, which is a data
# migration disguised as a bug fix.
# ---------------------------------------------------------------------

heading("The verdict gate, and what it does to rows it never measured")

check(
    "NULL coverage is not insufficient evidence",
    insufficient_evidence(RiskScore(coverage=None, source="rule_based")) is False,
)
check(
    "Coverage below the floor is",
    insufficient_evidence(RiskScore(coverage=0.50, source="rule_based")) is True,
)
check(
    "Coverage exactly at the floor is not",
    insufficient_evidence(
        RiskScore(coverage=MIN_EVIDENCE_COVERAGE, source="rule_based")
    ) is False,
    "the floor is a minimum, so equality passes",
)

explanation = describe_coverage(
    RiskScore(coverage=0.5, source="rule_based", missing_criteria="Assessment 1")
)
check(
    "The explanation names the share and the missing criterion",
    "50%" in explanation and "Assessment 1" in explanation,
    f"got {explanation!r}",
)


# ---------------------------------------------------------------------
# 6. End to end: the record that started this.
# ---------------------------------------------------------------------

heading("Mei Fujita, all the way through")

# A verdict needs BOTH engines staged, so this section runs only where
# the trained artifact loaded.
if not ml_available:
    print("    SKIP  a verdict needs both engines; the ML artifact did not load")
else:
    mei_verdict = compute_and_stage_final_verdict(db, mei.id, unit.id, WEEK)
    db.commit()

    check(
        "No tier is claimed for her",
        mei_verdict.final_tier is None,
        f"got {mei_verdict.final_tier!r}",
    )
    check(
        "She is sent to the review queue instead",
        mei_verdict.requires_review is True,
    )
    check(
        "The reason says a missing mark is not a passing mark",
        "missing mark is not a passing mark" in (mei_verdict.reason or ""),
        f"got {mei_verdict.reason!r}",
    )

    # The other half of the argument: the gate must not swallow students
    # whose records ARE complete. A guard that holds everyone back is
    # indistinguishable from a broken pipeline.
    compute_and_stage_ml_score(db, whole.id, unit.id, WEEK)
    db.commit()
    whole_verdict = compute_and_stage_final_verdict(db, whole.id, unit.id, WEEK)
    db.commit()
    check(
        "A fully marked student is not held back for thin evidence",
        "missing mark is not a passing mark" not in (whole_verdict.reason or ""),
        f"got {whole_verdict.reason!r}",
    )

    # And the boundary case: missing only the Moodle count is 96% of the
    # unit's weight, which is a student to score, not a student to queue.
    compute_and_stage_ml_score(db, nearly.id, unit.id, WEEK)
    db.commit()
    nearly_verdict = compute_and_stage_final_verdict(db, nearly.id, unit.id, WEEK)
    db.commit()
    check(
        "Missing only Moodle does not trigger a coverage hold",
        "missing mark is not a passing mark" not in (nearly_verdict.reason or ""),
        f"got {nearly_verdict.reason!r}",
    )


# ---------------------------------------------------------------------
# 7. Import warns about the cells it skips.
#
# The engines can now refuse to state a tier. That refusal is only
# actionable if the lecturer can see which marks are absent, and the
# only place they learn that is the upload result.
# ---------------------------------------------------------------------

heading("Blank cells are reported as warnings, not swallowed")

from app.services import ingestion_service  # noqa: E402 - after the fixture exists

rows = [
    {
        "student_number": "30001", "name": "Blank Assessments",
        "Attendance": "85.71", "Moodle": "16", "Assessment 1": "", "Assessment 2": None,
    },
]
column_map = {
    ATTENDANCE.id: "Attendance",
    MOODLE.id: "Moodle",
    ASSESSMENT_1.id: "Assessment 1",
    ASSESSMENT_2.id: "Assessment 2",
}

batch, errors, warnings, touched = ingestion_service.process_bulk_upload(
    db, rows=rows, unit_id=unit.id, lecturer_id=lecturer.id,
    filename="blank.csv", student_number_col="student_number", name_col="name",
    email_col=None, program_col=None, criteria_column_map=column_map,
)
db.commit()

check(
    "The blank cells produce a warning",
    len(warnings) == 1,
    f"got {warnings}",
)
check(
    "The row is NOT counted as an error",
    len(errors) == 0,
    f"got {errors}",
)
check(
    "The warning names both missing assessments",
    all(
        name in (warnings[0]["message"] if warnings else "")
        for name in ("Assessment 1", "Assessment 2")
    ),
    f"got {warnings[0]['message'] if warnings else None!r}",
)
check(
    "The warning names the student, not just the row number",
    "Blank Assessments" in (warnings[0]["message"] if warnings else ""),
)
check(
    "The values that WERE present still landed",
    batch.values_stored == 2,
    f"got {batch.values_stored}",
)
check(
    "values_failed counts errors only, not warnings",
    batch.values_failed == 0,
    f"got {batch.values_failed}",
)


# ---------------------------------------------------------------------

print("\n" + "=" * 60)
if failures:
    print(f"{len(failures)} FAILED:")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"All checks passed across {section} sections.")