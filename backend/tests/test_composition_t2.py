"""
Section T2 verification - unit composition rules + the admin shape API.

Run from `backend/`:

    PYTHONPATH=. python3 tests/test_composition_t2.py

THE SECTION THAT CARRIES THE MOST WEIGHT IS [4].

The runbook states the rule as `max_score = pct`, `weight = pct/100`.
That is exactly right for an assessment and catastrophic for the weekly
tutorial, and the failure is silent in all three directions:

  * a tutorial's stored score is ALREADY a completion percentage (0-100),
    produced by `rule_engine.calculate_tutorial_completion_pct`
  * with max_score = 10, `ingestion_service.validate_score` refuses every
    normal import ("Score 75.0 out of range ... valid range 0-10")
  * with max_score = 10, `rule_score_service.normalise_to_percentage`
    returns 75/10*100 = 750%, which clamps to zero badness - every
    student passes tutorials forever
  * `ml_score_service` divides by the same max_score, so the two engines
    AGREE on the wrong number and the hybrid layer never raises a review

Section [4] pins max_score = 100 for the tutorial and drives the real
`normalise_to_percentage` and `validate_score` functions to prove it.

Section [9] is the other one worth reading: a replace must NOT delete
attendance and Moodle, which are not in its payload.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models.student            # noqa: F401
import app.models.unit               # noqa: F401
import app.models.criteria           # noqa: F401
import app.models.user               # noqa: F401
import app.models.assessment_event   # noqa: F401
import app.models.ingestion_batch    # noqa: F401
import app.models.enrollment         # noqa: F401
import app.models.risk_score         # noqa: F401
import app.models.final_verdicts     # noqa: F401
import app.models.verdict_review     # noqa: F401
import app.models.rule_version       # noqa: F401
import app.models.student_note       # noqa: F401
import app.models.email_template     # noqa: F401
import app.models.email_message      # noqa: F401

from app.models.assessment_event import AssessmentEvent
from app.models.criteria import Criteria
from app.models.enums import (
    AssessmentKind, CriteriaCategory as Cat, EventSource, UserRole,
)
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.services import unit_composition as uc
from app.services.unit_composition import CompositionError, ShapeLockedError

NOW = datetime(2026, 8, 28, 9, 0, tzinfo=timezone.utc)

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


# ---------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
)
Base.metadata.create_all(engine)
db = Session(engine)

lecturer = User(email="l@example.com", full_name="Lecturer", hashed_password="x",
                role=UserRole.LECTURER, is_active=True)
admin = User(email="a@example.com", full_name="Admin", hashed_password="x",
             role=UserRole.ADMIN, is_active=True)
db.add_all([lecturer, admin])
db.flush()

_unit_seq = 0


def make_unit(code: str = "ICT729") -> Unit:
    """A freshly created unit: attendance and Moodle seeded, nothing else."""
    global _unit_seq
    _unit_seq += 1
    unit = Unit(unit_code=code, unit_name="Test Unit", year=2026,
                teaching_period=f"S{_unit_seq}", lecturer_id=lecturer.id,
                is_active=True, status="ASSIGNED")
    db.add(unit)
    db.flush()
    db.add(Criteria(unit_id=unit.id, name="Attendance", category=Cat.ATTENDANCE,
                    threshold=50.0, weight=0.5, max_score=100.0, enabled=True))
    db.add(Criteria(unit_id=unit.id, name="Moodle Activity", category=Cat.MOODLE,
                    threshold=10.0, weight=0.05, max_score=100.0, enabled=True))
    db.flush()
    return unit


_student_seq = 0


def make_student() -> Student:
    global _student_seq
    _student_seq += 1
    s = Student(name=f"Student {_student_seq}",
                student_number=f"T2{_student_seq:05d}",
                email=f"t2s{_student_seq}@example.com")
    db.add(s)
    db.flush()
    return s


def add_event(unit: Unit, criteria: Criteria, score: float) -> AssessmentEvent:
    e = AssessmentEvent(student_id=make_student().id, unit_id=unit.id,
                        criteria_id=criteria.id, score=score,
                        source=EventSource.BULK_UPLOAD, created_by=lecturer.id,
                        date=NOW.replace(tzinfo=None))
    db.add(e)
    db.flush()
    return e


def item(name, kind, pct, id=None):
    return {"id": id, "name": name, "kind": kind, "percentage": pct}


def refused(fn, *args, **kwargs):
    """The refusal message, or None if it went through."""
    try:
        fn(*args, **kwargs)
        return None
    except (CompositionError, ShapeLockedError) as exc:
        return str(exc)


QUIZ = AssessmentKind.QUIZ.value
ASSIGN = AssessmentKind.ASSIGNMENT.value


# ---------------------------------------------------------------------

heading("`kind` is a SECOND field - `category` is untouched")
# category is the ML contract: rule_score_service, ml_score_service,
# report_service, dashboard_service and student_detail_service all branch
# on CriteriaCategory.ASSESSMENT. Splitting it into QUIZ/ASSIGNMENT would
# have dropped every assessment out of every one of those branches.
check("CriteriaCategory still has exactly its four values",
      {m.value for m in Cat} == {"attendance", "weekly_tut", "assessment", "moodle"},
      str([m.value for m in Cat]))
check("AssessmentKind is quiz | assignment",
      {m.value for m in AssessmentKind} == {"quiz", "assignment"})
check("Criteria has a `kind` column", hasattr(Criteria, "kind"))
check("`kind` is nullable - every pre-T2 row keeps NULL",
      Criteria.__table__.c.kind.nullable is True)
check("no scoring service reads `kind`", not any(
    ".kind" in Path(f"app/services/{name}.py").read_text()
    for name in ("rule_score_service", "ml_score_service", "rule_engine",
                 "hybrid_engine")),
      "kind must stay a label; category is what the engines match on")

heading("The composition rules refuse what they should")
check("4 assessments are refused",
      refused(uc.validate_composition,
              [item(f"A{i}", ASSIGN, 10) for i in range(4)], False) is not None)
check("3 assessments are fine",
      refused(uc.validate_composition,
              [item(f"A{i}", ASSIGN, 10) for i in range(3)], False) is None)
check("a 21% quiz is refused",
      refused(uc.validate_composition, [item("Q", QUIZ, 21)], False) is not None)
check("a 20% quiz is allowed - the cap is inclusive",
      refused(uc.validate_composition, [item("Q", QUIZ, 20)], False) is None)
check("a 60% ASSIGNMENT is allowed - the cap is quizzes only",
      refused(uc.validate_composition, [item("A", ASSIGN, 60)], False) is None)
check("the quiz refusal suggests the way out",
      "assignment" in (refused(uc.validate_composition,
                               [item("Q", QUIZ, 50)], False) or "").lower())
check("a nameless item is refused",
      refused(uc.validate_composition, [item("   ", ASSIGN, 10)], False) is not None)
check("a kindless item is refused",
      refused(uc.validate_composition,
              [{"name": "A", "kind": None, "percentage": 10}], False) is not None)
check("an invented kind is refused",
      refused(uc.validate_composition,
              [{"name": "A", "kind": "exam", "percentage": 10}], False) is not None)
check("0% is refused", refused(
    uc.validate_composition, [item("A", ASSIGN, 0)], False) is not None)
check("a negative percentage is refused", refused(
    uc.validate_composition, [item("A", ASSIGN, -5)], False) is not None)

heading("The 100% budget - asymmetric on purpose")
check("101% is refused", refused(
    uc.validate_composition, [item("A", ASSIGN, 101)], False) is not None)
check("90 + 10 tutorial = 100 is allowed", refused(
    uc.validate_composition, [item("A", ASSIGN, 90)], True) is None)
check("95 + 10 tutorial = 105 is refused", refused(
    uc.validate_composition, [item("A", ASSIGN, 95)], True) is not None)
check("...and the refusal says the tutorial is in the total",
      "tutorial" in (refused(uc.validate_composition,
                             [item("A", ASSIGN, 95)], True) or "").lower())
check("95 WITHOUT tutorials is fine - the 10% is what tipped it",
      refused(uc.validate_composition, [item("A", ASSIGN, 95)], False) is None)
# Under 100% saves silently: a unit part-way through configuration is
# under 100% by definition, and scolding on every save is unusable.
check("30% total is accepted with no complaint", refused(
    uc.validate_composition, [item("A", ASSIGN, 30)], False) is None)
check("an EMPTY unit is a legal shape", refused(
    uc.validate_composition, [], False) is None)
check("tutorials alone is a legal shape", refused(
    uc.validate_composition, [], True) is None)
# 33.33 x 3 = 99.99000000000001 in binary floating point. An unrounded
# comparison refuses a shape that is visibly under 100%.
check("three items of 33.33 are not refused for floating-point dust",
      refused(uc.validate_composition,
              [item(f"A{i}", ASSIGN, 33.33) for i in range(3)], False) is None,
      str(uc.composition_total([item(f"A{i}", ASSIGN, 33.33) for i in range(3)],
                               False)))
check("the total is rounded", uc.composition_total(
    [item(f"A{i}", ASSIGN, 33.33) for i in range(3)], False) == 99.99)

heading("THE ONE THAT WOULD HAVE BROKEN SCORING SILENTLY")
# `max_score = pct` is right for an assessment and wrong for the tutorial.
check("a 30% assessment is marked out of 30",
      uc.assessment_row_values(30)["max_score"] == 30.0)
check("...and weighs 0.30", uc.assessment_row_values(30)["weight"] == 0.30)
check("a 20% quiz is marked out of 20",
      uc.assessment_row_values(20)["max_score"] == 20.0)

tut = uc.tutorial_row_values()
check("THE TUTORIAL'S max_score IS 100, NOT 10", tut["max_score"] == 100.0,
      f"got {tut['max_score']} - see the module docstring")
check("its 10% is carried entirely by the weight", tut["weight"] == 0.10)

# Drive the REAL functions, not a restatement of them.
from app.services.rule_score_service import normalise_to_percentage  # noqa: E402
from app.services.ingestion_service import validate_score            # noqa: E402
import inspect                                                       # noqa: E402

tut_row = Criteria(unit_id=1, name="Weekly Tutorials", category=Cat.WEEKLY_TUT,
                   threshold=50.0, **tut)
check("a 75% completion normalises to 75%, not 750%",
      normalise_to_percentage(75.0, tut_row) == 75.0,
      str(normalise_to_percentage(75.0, tut_row)))

broken = Criteria(unit_id=1, name="Weekly Tutorials", category=Cat.WEEKLY_TUT,
                  threshold=50.0, max_score=10.0, weight=0.10)
check("...and the naive max_score=10 really would have produced 750%",
      normalise_to_percentage(75.0, broken) == 750.0,
      "proving the trap is real, not theoretical")

# Argument order pinned so a signature change fails here rather than
# quietly comparing a Criteria against an int at ingestion time.
check("validate_score takes (criteria, score)",
      list(inspect.signature(validate_score).parameters) == ["criteria", "score"],
      str(inspect.signature(validate_score)))
check("a 75% completion passes ingestion's range check",
      validate_score(tut_row, 75.0) is None, str(validate_score(tut_row, 75.0)))
check("...and would have been rejected as out of range at max_score=10",
      validate_score(broken, 75.0) is not None,
      "a normal tutorial import would have failed as a data error")

assess_row = Criteria(unit_id=1, name="Quiz 1", category=Cat.ASSESSMENT,
                      threshold=50.0, **uc.assessment_row_values(20))
check("an assessment DOES divide by its own max_score: 15/20 -> 75%",
      normalise_to_percentage(15.0, assess_row) == 75.0)

heading("Pass marks are derived, never stored")
check("30 marks at a 50% bar -> pass mark 15", uc.pass_mark(
    Criteria(unit_id=1, name="A", max_score=30.0, threshold=50.0)) == 15.0)
check("20 marks at a 45% bar -> pass mark 9", uc.pass_mark(
    Criteria(unit_id=1, name="A", max_score=20.0, threshold=45.0)) == 9.0)
check("the tutorial's 50% bar is 50% completion", uc.pass_mark(tut_row) == 50.0)
check("a missing max_score gives None, not a crash", uc.pass_mark(
    Criteria(unit_id=1, name="A", max_score=None, threshold=50.0)) is None)
check("there is no pass_mark COLUMN", not hasattr(Criteria, "pass_mark"),
      "a stored one would need rewriting on every T4 slider move")

heading("A replace materialises the shape")
u = make_unit("ICT701")
shape = uc.replace_unit_shape(db, u, [
    item("Quiz 1", QUIZ, 20), item("Assignment 1", ASSIGN, 40),
], tutorials_enabled=True)
db.commit()

check("two assessments were created", len(shape["assessments"]) == 2)
check("tutorials are on", shape["tutorials_enabled"] is True)
check("the total is 70%", shape["total_percentage"] == 70.0,
      str(shape["total_percentage"]))
check("40% is left", shape["remaining_percentage"] == 30.0,
      str(shape["remaining_percentage"]) + " (20+40+10 = 70)")
check("the unit now reads as configured", shape["configured"] is True)
check("the quiz kept its kind", shape["assessments"][0]["kind"] == "quiz")
check("slots are numbered 1..n",
      [row["sequence_number"] for row in shape["assessments"]] == [1, 2])
check("the quiz is marked out of 20", shape["assessments"][0]["max_score"] == 20.0)
check("its pass mark is 10", shape["assessments"][0]["pass_mark"] == 10.0)
check("the tutorial row is on the 0-100 scale",
      shape["tutorial"]["max_score"] == 100.0)
check("the tutorial's PERCENTAGE still reads 10, not 100",
      shape["tutorial"]["percentage"] == 10.0,
      "read off weight, not max_score - that is the whole point")
check("every assessment is category=assessment", all(
    row["category"] == "assessment" for row in shape["assessments"]))
check("a fresh item starts at the default 50% bar", all(
    row["threshold"] == 50.0 for row in shape["assessments"]))

heading("An empty unit is NOT configured")
blank = make_unit("ICT702")
blank_shape = uc.get_unit_shape(db, blank)
check("a newly created unit reads as not configured",
      blank_shape["configured"] is False,
      "attendance and Moodle exist from creation and must not count")
check("...but its automatic criteria ARE reported",
      len(blank_shape["automatic"]) == 2)
check("the limits are sent to the client",
      blank_shape["limits"]["quiz_max_percentage"] == 20.0)
check("total is 0%", blank_shape["total_percentage"] == 0.0)

heading("ATTENDANCE AND MOODLE SURVIVE A REPLACE - the other one that matters")
# "Replace" means "replace the assessments and the tutorial", NOT "delete
# every criterion not named in the payload". Attendance and Moodle are
# seeded once at unit creation and carry 55% of the rule blend between
# them; a literal replace would delete both on the first save.
before = {c.category for c in db.query(Criteria).filter(
    Criteria.unit_id == u.id, Criteria.enabled.is_(True)).all()}
uc.replace_unit_shape(db, u, [item("Assignment 1", ASSIGN, 50)],
                      tutorials_enabled=False)
db.commit()
after = db.query(Criteria).filter(Criteria.unit_id == u.id,
                                  Criteria.enabled.is_(True)).all()
check("attendance survived", any(c.category == Cat.ATTENDANCE for c in after))
check("Moodle survived", any(c.category == Cat.MOODLE for c in after))
check("attendance kept its fixed weight", next(
    c for c in after if c.category == Cat.ATTENDANCE).weight == 0.5)
check("attendance kept max_score 100", next(
    c for c in after if c.category == Cat.ATTENDANCE).max_score == 100.0)
check("the tutorial was switched off",
      not any(c.category == Cat.WEEKLY_TUT for c in after))
check("only one assessment remains",
      len([c for c in after if c.category == Cat.ASSESSMENT]) == 1)
check("Cat.ATTENDANCE and Cat.MOODLE were in the unit before too",
      Cat.ATTENDANCE in before and Cat.MOODLE in before)

heading("Removing an item with marks DISABLES it, never deletes it")
withdata = make_unit("ICT703")
uc.replace_unit_shape(db, withdata, [
    item("Quiz 1", QUIZ, 20), item("Assignment 1", ASSIGN, 30),
], tutorials_enabled=False)
db.commit()
doomed = db.query(Criteria).filter(
    Criteria.unit_id == withdata.id, Criteria.name == "Assignment 1").one()
doomed_id = doomed.id
add_event(withdata, doomed, 25.0)
db.commit()

# It is locked now, so open the one-shot window first.
uc.unlock_shape(db, withdata, "ICT703", actor_id=admin.id, now=NOW)
uc.replace_unit_shape(db, withdata, [item("Quiz 1", QUIZ, 20)],
                      tutorials_enabled=False)
db.commit()

survivor = db.get(Criteria, doomed_id)
check("the removed row still exists", survivor is not None)
check("...but is disabled", survivor.enabled is False)
check("its AssessmentEvent history is intact",
      db.query(AssessmentEvent).filter(
          AssessmentEvent.criteria_id == doomed_id).count() == 1,
      "hard-deleting would break the FK or orphan real ingested data")
check("the disabled row is gone from the shape",
      len(uc.get_unit_shape(db, withdata)["assessments"]) == 1)

heading("A rename keeps the row, and its history, and its pass bar")
renamed_unit = make_unit("ICT704")
uc.replace_unit_shape(db, renamed_unit, [item("Quiz 1", QUIZ, 20)],
                      tutorials_enabled=False)
db.commit()
row = db.query(Criteria).filter(Criteria.unit_id == renamed_unit.id,
                                Criteria.category == Cat.ASSESSMENT).one()
original_id = row.id
row.threshold = 46.0                      # a lecturer moved the T4 bar
add_event(renamed_unit, row, 12.0)
db.commit()
# The setup replace above WAS a shape change and stamped this. What the
# rename must not do is move it again.
stamp_before_rename = renamed_unit.criteria_updated_at
check("the setup replace stamped criteria_updated_at",
      stamp_before_rename is not None)

after_rename = uc.replace_unit_shape(
    db, renamed_unit, [item("Week 4 Quiz", QUIZ, 20, id=original_id)],
    tutorials_enabled=False)
db.commit()
check("the rename went through on a LOCKED unit",
      after_rename["assessments"][0]["name"] == "Week 4 Quiz")
check("it is the same row", after_rename["assessments"][0]["id"] == original_id)
check("the lecturer's 46% bar was NOT reset to 50",
      after_rename["assessments"][0]["threshold"] == 46.0,
      "a whole-object replace must not silently undo the T4 slider")
check("the derived pass mark moved with it",
      after_rename["assessments"][0]["pass_mark"] == 9.2, "20 * 0.46")
check("a rename did NOT bump criteria_updated_at",
      renamed_unit.criteria_updated_at == stamp_before_rename,
      "T1: a label is not a rule, in this write path too")

heading("Change classification: none / labels_only / shape")
current = uc.get_unit_shape(db, renamed_unit)
check("an identical payload is 'none'", uc.classify_shape_change(
    current, [item("Week 4 Quiz", QUIZ, 20)], False) == "none")
check("a name-only change is 'labels_only'", uc.classify_shape_change(
    current, [item("Renamed", QUIZ, 20)], False) == "labels_only")
check("a percentage change is 'shape'", uc.classify_shape_change(
    current, [item("Week 4 Quiz", QUIZ, 15)], False) == "shape")
check("a kind change is 'shape'", uc.classify_shape_change(
    current, [item("Week 4 Quiz", ASSIGN, 20)], False) == "shape")
check("turning tutorials on is 'shape'", uc.classify_shape_change(
    current, [item("Week 4 Quiz", QUIZ, 20)], True) == "shape")
check("adding an item is 'shape'", uc.classify_shape_change(
    current, [item("Week 4 Quiz", QUIZ, 20), item("A2", ASSIGN, 10)],
    False) == "shape")
check("removing everything is 'shape'",
      uc.classify_shape_change(current, [], False) == "shape")

heading("The lock (T1) governs this write path too")
locked = make_unit("ICT705")
uc.replace_unit_shape(db, locked, [item("Quiz 1", QUIZ, 20)],
                      tutorials_enabled=False)
db.commit()
qrow = db.query(Criteria).filter(Criteria.unit_id == locked.id,
                                 Criteria.category == Cat.ASSESSMENT).one()
add_event(locked, qrow, 15.0)
db.commit()

check("the unit is locked", uc.shape_lock_state(db, locked)["state"] == "locked")
locked_stamp = locked.criteria_updated_at

def _locked_error(*args, **kwargs):
    try:
        uc.replace_unit_shape(*args, **kwargs)
        return None
    except ShapeLockedError as exc:
        db.rollback()
        return str(exc)
    except CompositionError as exc:                       # pragma: no cover
        db.rollback()
        return f"WRONG-TYPE: {exc}"


check("a percentage change on a locked unit is refused",
      (_locked_error(db, locked, [item("Quiz 1", QUIZ, 15)], False) or ""
       ).startswith("This unit's criteria are locked"),
      str(_locked_error(db, locked, [item("Quiz 1", QUIZ, 15)], False)))
check("an IDENTICAL payload is accepted while locked",
      _locked_error(db, locked, [item("Quiz 1", QUIZ, 20, id=qrow.id)],
                    False) is None,
      "the form GETs then PUTs - pressing Save unchanged must not 409")
check("...and it did not move criteria_updated_at",
      locked.criteria_updated_at == locked_stamp)
check("a rename is accepted while locked",
      _locked_error(db, locked, [item("Renamed Quiz", QUIZ, 20, id=qrow.id)],
                    False) is None)
db.commit()
check("...and still did not move criteria_updated_at",
      locked.criteria_updated_at == locked_stamp,
      "labels_only must not mark a cohort's results stale")

heading("Unlock is still one-shot through the shape API")
uc.unlock_shape(db, locked, "ICT705", actor_id=admin.id, now=NOW)
db.commit()
check("the window is open", locked.criteria_unlocked_at is not None)
uc.replace_unit_shape(db, locked, [item("Renamed Quiz", QUIZ, 15, id=qrow.id)],
                      tutorials_enabled=False)
db.commit()
check("the shape change went through",
      uc.get_unit_shape(db, locked)["assessments"][0]["percentage"] == 15.0)
check("the window closed on the save", locked.criteria_unlocked_at is None)
check("criteria_updated_at moved on the real save",
      locked.criteria_updated_at is not None
      and locked.criteria_updated_at != locked_stamp,
      f"{locked_stamp} -> {locked.criteria_updated_at}")
check("a second change is refused",
      _locked_error(db, locked, [item("Renamed Quiz", QUIZ, 10, id=qrow.id)],
                    False) is not None)

heading("A composition breach never half-writes")
partial = make_unit("ICT706")
uc.replace_unit_shape(db, partial, [item("Quiz 1", QUIZ, 20)],
                      tutorials_enabled=False)
db.commit()
before_rows = [(c.name, c.weight) for c in db.query(Criteria).filter(
    Criteria.unit_id == partial.id, Criteria.enabled.is_(True)).all()]
err = refused(uc.replace_unit_shape, db, partial,
              [item("Quiz 1", QUIZ, 20), item("Huge", ASSIGN, 95)], False)
check("the over-budget shape is refused", err is not None)
check("it is a CompositionError, not a lock error",
      "more than 100" in (err or ""), str(err))
after_rows = [(c.name, c.weight) for c in db.query(Criteria).filter(
    Criteria.unit_id == partial.id, Criteria.enabled.is_(True)).all()]
check("nothing was written before the refusal", before_rows == after_rows,
      "validation runs before the first setattr, so no rollback is needed")

heading("LIVE HTTP: the admin shape endpoints over the wire")
from fastapi import FastAPI                                       # noqa: E402
from fastapi.testclient import TestClient                         # noqa: E402
from app.api.routes.admin_criteria import router as shape_router  # noqa: E402
from app.core.dependencies import get_current_user                # noqa: E402
from app.database import get_db                                   # noqa: E402

api = FastAPI()
api.include_router(shape_router)
acting_as = {"user": admin}
api.dependency_overrides[get_db] = lambda: db
api.dependency_overrides[get_current_user] = lambda: acting_as["user"]
client = TestClient(api)

http_unit = make_unit("ICT800")
db.commit()
base = f"/admin/units/{http_unit.id}/criteria"

got = client.get(base)
check("GET returns 200", got.status_code == 200, got.text)
check("...and reports not configured", got.json()["configured"] is False)
check("...and carries the lock state in the same response",
      got.json()["lock"]["state"] == "draft", got.text)

put = client.put(base, json={
    "assessments": [
        {"name": "Quiz 1", "kind": "quiz", "percentage": 20},
        {"name": "Report", "kind": "assignment", "percentage": 45},
    ],
    "tutorials_enabled": True,
})
check("PUT returns 200", put.status_code == 200, put.text)
check("...with the new total", put.json()["total_percentage"] == 75.0, put.text)
check("...and real database ids for the new rows",
      all(row["id"] for row in put.json()["assessments"]), put.text)

over = client.put(base, json={
    "assessments": [{"name": "Huge", "kind": "assignment", "percentage": 95}],
    "tutorials_enabled": True,
})
check("an over-budget PUT is 400", over.status_code == 400,
      f"{over.status_code} {over.text}")
check("the 400 explains the arithmetic", "100" in over.json()["detail"])

bad_quiz = client.put(base, json={
    "assessments": [{"name": "Q", "kind": "quiz", "percentage": 30}],
    "tutorials_enabled": False,
})
check("a 30% quiz is 400", bad_quiz.status_code == 400, bad_quiz.text)

too_many = client.put(base, json={
    "assessments": [{"name": f"A{i}", "kind": "assignment", "percentage": 10}
                    for i in range(4)],
    "tutorials_enabled": False,
})
check("four assessments is 400", too_many.status_code == 400, too_many.text)

malformed = client.put(base, json={
    "assessments": [{"name": "X", "kind": "exam", "percentage": 10}],
    "tutorials_enabled": False,
})
check("an invented kind is 422 from pydantic, not 400",
      malformed.status_code == 422, f"{malformed.status_code} {malformed.text}")

check("the shape survived every refusal",
      client.get(base).json()["total_percentage"] == 75.0,
      client.get(base).text)

# Lock it and prove the three status codes stay distinct over HTTP.
live_row = db.query(Criteria).filter(
    Criteria.unit_id == http_unit.id, Criteria.name == "Quiz 1").one()
add_event(http_unit, live_row, 15.0)
db.commit()
check("GET now reports locked", client.get(base).json()["lock"]["state"] == "locked")

conflict = client.put(base, json={
    "assessments": [{"name": "Quiz 1", "kind": "quiz", "percentage": 10}],
    "tutorials_enabled": True,
})
check("a locked shape change is 409, not 400", conflict.status_code == 409,
      f"{conflict.status_code} {conflict.text}")

current_payload = {
    "assessments": [
        {"id": row["id"], "name": row["name"], "kind": row["kind"],
         "percentage": row["percentage"]}
        for row in client.get(base).json()["assessments"]
    ],
    "tutorials_enabled": True,
}
check("re-saving the unchanged shape while locked is 200",
      client.put(base, json=current_payload).status_code == 200,
      "GET-then-PUT is exactly what the T3 form does")

acting_as["user"] = lecturer
check("a lecturer cannot read the shape (403)",
      client.get(base).status_code == 403)
check("a lecturer cannot write it (403)",
      client.put(base, json=current_payload).status_code == 403,
      "a lecturer reshaping a unit is precisely what T4 must not allow")
acting_as["user"] = admin
check("an unknown unit is 404",
      client.get("/admin/units/999999/criteria").status_code == 404)

heading("The wiring is real, not just written")
main_source = Path("main.py").read_text()
check("the router is registered in main.py",
      "admin_criteria_router" in main_source
      and "app.include_router(admin_criteria_router)" in main_source,
      "eight cases of configured-but-never-called in this project already")

import main as app_main                                            # noqa: E402
paths = app_main.app.openapi()["paths"]
check("the full app exposes GET /admin/units/{unit_id}/criteria",
      "get" in paths.get("/admin/units/{unit_id}/criteria", {}), str(
          sorted(p for p in paths if "criteria" in p)))
check("...and PUT",
      "put" in paths.get("/admin/units/{unit_id}/criteria", {}))
check("the lecturer's per-item routes are untouched",
      "/units/{unit_id}/criteria/{criteria_id}" in paths)
check("the two prefixes do not collide",
      "/admin/units/{unit_id}" in paths
      and "/admin/units/{unit_id}/criteria" in paths,
      "unit lifecycle and unit shape are different paths")

heading("The migration matches the model")
migration = Path("alembic/versions/a6b7c8d9e0f1_add_kind_to_criteria.py").read_text()
check("it adds `kind`", '"kind"' in migration)
check("it follows T1's migration",
      'down_revision = "f5a6b7c8d9e0"' in migration)
check("nothing is back-filled", "UPDATE criteria" not in migration,
      "guessing a kind from a free-text name would store a fabricated fact")
check("downgrade drops the column",
      migration.split("def downgrade")[1].count("drop_column") == 1)
check("downgrade drops the enum type AFTER the column",
      migration.split("def downgrade")[1].index("drop_column")
      < migration.split("def downgrade")[1].index("KIND_ENUM.drop"),
      "a type still referenced by a column cannot be dropped")
check("the enum name matches the model's",
      'name="assessmentkind"' in migration
      and 'name="assessmentkind"' in Path("app/models/criteria.py").read_text())

heading("Migration upgrade() and downgrade() actually run")
from alembic.migration import MigrationContext                     # noqa: E402
from alembic.operations import Operations                          # noqa: E402
from sqlalchemy import create_engine as _ce, inspect as _inspect    # noqa: E402

mig_engine = _ce("sqlite://", connect_args={"check_same_thread": False},
                 poolclass=StaticPool)
Base.metadata.create_all(mig_engine)
with mig_engine.connect() as conn:
    conn.execute(__import__("sqlalchemy").text(
        "ALTER TABLE criteria DROP COLUMN kind"))
    conn.commit()
    cols = {c["name"] for c in _inspect(conn).get_columns("criteria")}
    check("kind is absent before the upgrade", "kind" not in cols)

    ctx = MigrationContext.configure(conn)

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "t2_migration", "alembic/versions/a6b7c8d9e0f1_add_kind_to_criteria.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # `Operations.context` installs the `alembic.op` proxy for the block,
    # which is what lets a migration file's plain `op.add_column(...)`
    # calls run against this connection.
    with Operations.context(ctx):
        module.upgrade()
    cols = {c["name"] for c in _inspect(conn).get_columns("criteria")}
    check("upgrade() added kind", "kind" in cols, str(sorted(cols)))

    with Operations.context(ctx):
        module.downgrade()
    cols = {c["name"] for c in _inspect(conn).get_columns("criteria")}
    check("downgrade() removed it again", "kind" not in cols, str(sorted(cols)))
    check("downgrade left the rest of the table alone",
          {"id", "unit_id", "name", "weight", "threshold", "max_score",
           "category", "sequence_number", "enabled"}.issubset(cols),
          str(sorted(cols)))

heading("Alembic still has a single head")
from alembic.config import Config                                  # noqa: E402
from alembic.script import ScriptDirectory                         # noqa: E402

script = ScriptDirectory.from_config(Config("alembic.ini"))
heads = script.get_heads()
check("exactly one head", len(heads) == 1, str(heads))
# AMENDED BY PHASE EMAIL. This pinned T2's migration as the tip of the
# chain, which was true until the acknowledgment migration was added on
# top of it. What T2 actually needs to guarantee is that the graph has
# not FORKED and that T2 is still on the path - not that nothing has
# been built since. Pinning a tip makes every later migration a test
# failure in an unrelated suite.
check("exactly one head - the graph has not forked", len(heads) == 1, str(heads))
check("...and T2's revision is still in the chain",
      "a6b7c8d9e0f1" in {revision.revision for revision in script.walk_revisions()},
      str(heads))

print("\n" + "=" * 60)
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections)")