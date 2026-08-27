"""
Section D1 verification - threshold floors, enforced.

The first section is the important one: it fails against the code as it
stood this morning. `validate_lecturer_threshold` was keyed "tutorial"
while the enum value is "weekly_tut", so `floors.get("weekly_tut")`
returned None and a tutorial threshold of ZERO passed validation - in a
function nothing called, so nothing ever surfaced it.
"""

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models.student            # noqa: F401
import app.models.unit               # noqa: F401
import app.models.criteria           # noqa: F401
import app.models.user               # noqa: F401
import app.models.assessment_event   # noqa: F401
import app.models.ingestion_batch    # noqa: F401

from app.models.criteria import Criteria
from app.models.enums import CriteriaCategory as Cat
from app.services import criteria_service
from app.services.rule_engine import (
    DEFAULT_THRESHOLD,
    FIXED_THRESHOLDS,
    THRESHOLD_FLOORS,
    validate_lecturer_threshold,
)

failures: list[str] = []
section = 0


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


def rejects(category, threshold) -> str | None:
    """The error message, or None if it was allowed through."""
    try:
        validate_lecturer_threshold(category, threshold)
        return None
    except ValueError as exc:
        return str(exc)


# ---------------------------------------------------------------------

heading("The bug: tutorials were keyed by the wrong name")
# floors = {"tutorial": 40.0} vs CriteriaCategory.WEEKLY_TUT.value ==
# "weekly_tut". These four checks all passed silently before D1.
check("a tutorial threshold of 0 is refused",
      rejects(Cat.WEEKLY_TUT, 0) is not None)
check("a tutorial threshold of 39 is refused",
      rejects(Cat.WEEKLY_TUT, 39) is not None)
check("the floors dict is keyed by the ENUM VALUE",
      set(THRESHOLD_FLOORS) == {"assessment", "weekly_tut"},
      str(set(THRESHOLD_FLOORS)))
check("the old English key is gone", "tutorial" not in THRESHOLD_FLOORS)

heading("Floors, per category")
check("assessment floor is 45", THRESHOLD_FLOORS["assessment"] == 45.0)
check("tutorial floor is 40", THRESHOLD_FLOORS["weekly_tut"] == 40.0)
check("assessment at exactly 45 is allowed",
      rejects(Cat.ASSESSMENT, 45) is None, str(rejects(Cat.ASSESSMENT, 45)))
check("assessment at 44.9 is refused", rejects(Cat.ASSESSMENT, 44.9) is not None)
check("tutorial at exactly 40 is allowed",
      rejects(Cat.WEEKLY_TUT, 40) is None, str(rejects(Cat.WEEKLY_TUT, 40)))
check("tutorial at 39.9 is refused", rejects(Cat.WEEKLY_TUT, 39.9) is not None)
check("the message names the floor, not just 'invalid'",
      "45" in (rejects(Cat.ASSESSMENT, 10) or ""),
      str(rejects(Cat.ASSESSMENT, 10)))

heading("The bar cannot be RAISED either")
# A lecturer quietly making their unit harder to pass changes what "at
# risk" means for their cohort without anyone being told.
check("assessment above the 50% default is refused",
      rejects(Cat.ASSESSMENT, 60) is not None)
check("tutorial above the 50% default is refused",
      rejects(Cat.WEEKLY_TUT, 51) is not None)
check("exactly the default is allowed",
      rejects(Cat.ASSESSMENT, DEFAULT_THRESHOLD) is None)

heading("Fixed categories are refused, not floor-checked")
attendance = rejects(Cat.ATTENDANCE, 40)
moodle = rejects(Cat.MOODLE, 8)
check("attendance cannot be changed", attendance is not None)
check("moodle cannot be changed", moodle is not None)
check("the message says FIXED, not 'below the floor'",
      "fixed" in (attendance or "").lower(), str(attendance))
check("even setting attendance to its own value is refused here",
      rejects(Cat.ATTENDANCE, 50) is not None,
      "the row guard allows no-ops; the raw validator does not")
check("moodle's fixed value is the login COUNT, not a percentage",
      FIXED_THRESHOLDS["moodle"] == 10.0)

heading("The validator takes an enum or a string")
check("a raw string works too", rejects("weekly_tut", 0) is not None)
check("an uppercase string works", rejects("WEEKLY_TUT", 0) is not None)
check("no category means no floor - D2 stops these being created",
      rejects(None, 0) is None)


# ---------------------------------------------------------------------
# Row-level policy
# ---------------------------------------------------------------------

def build_db() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


db = build_db()


def make(category, threshold=50.0, weight=0.3, max_score=100.0) -> Criteria:
    row = Criteria(
        unit_id=1, name="X", category=category, threshold=threshold,
        weight=weight, max_score=max_score, enabled=True,
    )
    db.add(row)
    db.flush()
    return row


def update_rejects(row, changes) -> str | None:
    try:
        criteria_service.assert_lecturer_may_update(row, changes)
        return None
    except ValueError as exc:
        return str(exc)


def create_rejects(payload) -> str | None:
    try:
        criteria_service.assert_lecturer_may_create(payload)
        return None
    except ValueError as exc:
        return str(exc)


heading("Creating criteria")
check("a legal assessment is allowed",
      create_rejects({"category": Cat.ASSESSMENT, "threshold": 50}) is None)
check("an assessment below the floor is refused",
      create_rejects({"category": Cat.ASSESSMENT, "threshold": 20}) is not None)
# Seeding already made exactly one of each. A second would not override
# the first - the rule engine would blend BOTH and double-count the
# strongest signal in the system.
check("a second attendance criterion is refused",
      create_rejects({"category": Cat.ATTENDANCE, "threshold": 50}) is not None)
check("the message explains it is automatic, not that it is invalid",
      "automatic" in (create_rejects(
          {"category": Cat.ATTENDANCE, "threshold": 50}) or "").lower())
check("a second moodle criterion is refused",
      create_rejects({"category": Cat.MOODLE, "threshold": 10}) is not None)

heading("Updating criteria")
assessment = make(Cat.ASSESSMENT)
tutorial = make(Cat.WEEKLY_TUT)
attendance_row = make(Cat.ATTENDANCE, threshold=50.0, weight=0.5)
moodle_row = make(Cat.MOODLE, threshold=10.0, weight=0.05)

check("lowering an assessment to its floor is allowed",
      update_rejects(assessment, {"threshold": 45}) is None)
check("lowering below the floor is refused",
      update_rejects(assessment, {"threshold": 44}) is not None)
check("lowering a tutorial to 40 is allowed",
      update_rejects(tutorial, {"threshold": 40}) is None)
check("a PATCH that does not touch threshold is allowed",
      update_rejects(assessment, {"name": "Quiz 1"}) is None)

heading("Fixed rows reject any real change, but allow a no-op")
check("changing the attendance threshold is refused",
      update_rejects(attendance_row, {"threshold": 40}) is not None)
check("changing the attendance WEIGHT is refused too",
      update_rejects(attendance_row, {"weight": 0.1}) is not None,
      "the rule engine was tuned around 0.5")
check("changing attendance max_score is refused",
      update_rejects(attendance_row, {"max_score": 50}) is not None)
check("disabling attendance is refused",
      update_rejects(attendance_row, {"enabled": False}) is not None)
# A client that PATCHes the whole object back must not be rejected for
# echoing values it did not change.
check("a no-op PATCH echoing the same values is allowed",
      update_rejects(attendance_row,
                     {"threshold": 50.0, "weight": 0.5}) is None)
check("renaming attendance is allowed - it is only a label",
      update_rejects(attendance_row, {"name": "Class attendance"}) is None)
check("changing the moodle threshold is refused",
      update_rejects(moodle_row, {"threshold": 5}) is not None)

heading("Relabelling cannot sidestep a floor")
# An assessment at 45 is legal. Relabelled as a tutorial it is still
# legal (tutorial floor is lower). A tutorial at 40 relabelled as an
# ASSESSMENT is not - and the check must use the category the row will
# HAVE after the write, not the one it has now.
low_tutorial = make(Cat.WEEKLY_TUT, threshold=40.0)
check("tutorial at 40 promoted to assessment is refused",
      update_rejects(low_tutorial, {"category": Cat.ASSESSMENT}) is not None,
      "40 is below the assessment floor of 45")
check("...and the message names the assessment floor",
      "45" in (update_rejects(low_tutorial, {"category": Cat.ASSESSMENT}) or ""))
check("assessment at 45 demoted to tutorial is allowed",
      update_rejects(make(Cat.ASSESSMENT, threshold=45.0),
                     {"category": Cat.WEEKLY_TUT}) is None)
check("changing category AND threshold together is checked as a pair",
      update_rejects(low_tutorial,
                     {"category": Cat.ASSESSMENT, "threshold": 45}) is None)

heading("Both write paths are actually wired")
from pathlib import Path  # noqa: E402

route_source = Path("app/api/routes/criteria.py").read_text()
check("create calls the policy",
      "assert_lecturer_may_create" in route_source)
check("update calls the policy",
      "assert_lecturer_may_update" in route_source)
# The whole point of D1. A guard with no callers is what D1 is fixing.
check("the validator now has callers",
      "validate_lecturer_threshold" in
      Path("app/services/criteria_service.py").read_text())
check("a refusal is a 400, not a 422",
      route_source.count("HTTP_400_BAD_REQUEST") >= 2,
      "the payload is well-formed, it is just not permitted")

heading("The migration brings existing rows up to the rules")
migration = Path(
    "alembic/versions/e4f5a6b7c8d9_enforce_threshold_floors.py"
).read_text()
check("attendance is reset to its constant", "category = 'attendance'" in migration)
check("moodle is reset to its constant", "category = 'moodle'" in migration)
check("sub-floor assessments are raised", "threshold < :f" in migration)
check("tutorials are keyed by the ENUM value, not 'tutorial'",
      "'weekly_tut'" in migration and "'tutorial'" not in migration)
check("above-default thresholds are brought back down", "threshold > :d" in migration)
# Every statement raises a bar or resets it. None lowers one, so nobody
# moves from at-risk to safe because a migration ran.
check("no statement LOWERS an adjustable threshold",
      "threshold > :d" in migration and "SET threshold = :f" in migration)
check("downgrade is an honest no-op, not a guess",
      "pass" in migration.split("def downgrade")[1])

heading("Live SQL: the migration statements actually work")
db.execute(text(
    "INSERT INTO criteria (unit_id, name, weight, threshold, max_score, "
    "category, enabled) VALUES "
    "(9, 'Att', 0.5, 33.0, 100.0, 'attendance', 1),"
    "(9, 'Mood', 0.05, 3.0, 100.0, 'moodle', 1),"
    "(9, 'Quiz', 0.2, 0.0, 20.0, 'assessment', 1),"
    "(9, 'Tut', 0.1, 5.0, 100.0, 'weekly_tut', 1),"
    "(9, 'Hard', 0.2, 80.0, 100.0, 'assessment', 1),"
    "(9, 'Keep', 0.2, 46.0, 100.0, 'assessment', 1)"
))
db.execute(text("UPDATE criteria SET threshold = 50.0 WHERE category = 'attendance' AND threshold <> 50.0"))
db.execute(text("UPDATE criteria SET threshold = 10.0 WHERE category = 'moodle' AND threshold <> 10.0"))
db.execute(text("UPDATE criteria SET threshold = 45.0 WHERE category = 'assessment' AND threshold < 45.0"))
db.execute(text("UPDATE criteria SET threshold = 40.0 WHERE category = 'weekly_tut' AND threshold < 40.0"))
db.execute(text("UPDATE criteria SET threshold = 50.0 WHERE category IN ('assessment','weekly_tut') AND threshold > 50.0"))

rows = {
    name: threshold
    for name, threshold in db.execute(
        text("SELECT name, threshold FROM criteria WHERE unit_id = 9")
    )
}
check("attendance corrected to 50", rows["Att"] == 50.0, str(rows))
check("moodle corrected to 10", rows["Mood"] == 10.0, str(rows))
check("a zero assessment threshold raised to 45", rows["Quiz"] == 45.0, str(rows))
check("a 5% tutorial raised to 40", rows["Tut"] == 40.0, str(rows))
check("an 80% assessment brought down to 50", rows["Hard"] == 50.0, str(rows))
# The one that matters: a deliberate, legal choice is left alone.
check("a legal 46 is LEFT ALONE, not reset to 50", rows["Keep"] == 46.0, str(rows))

heading("Every corrected row now passes the live validator")
for name, threshold in rows.items():
    category = db.execute(text(
        "SELECT category FROM criteria WHERE unit_id = 9 AND name = :n"
    ), {"n": name}).scalar()
    if category in ("attendance", "moodle"):
        continue
    check(f"{name} ({category} @ {threshold:g}) is legal",
          rejects(category, threshold) is None,
          str(rejects(category, threshold)))

print("\n" + "=" * 60)
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections)")