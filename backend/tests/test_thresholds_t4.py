"""
Section T4 verification - the lecturer's threshold bar.

Run from `backend/`:

    PYTHONPATH=. python3 tests/test_thresholds_t4.py

THE SECTION THAT CARRIES THE MOST WEIGHT IS [5].

A unit is locked (T1) exactly when assessment marks have been imported
or an analysis has run - which is exactly when a lecturer looks at their
at-risk list and decides the bar is in the wrong place. If the shape
lock covered the threshold, the slider would be editable ONLY on units
where it changes nothing anyone can see, and every real use would route
through an admin unlock. Section [5] pins that a bar change goes through
on a locked unit, and section [6] pins the other half of the bargain:
it still marks the unit's analyses stale, so the report says so.

Section [3] is the other one worth reading: two assessments on
DIFFERENT bars must be reported as `mixed`, not as whichever row came
first - otherwise one slider drag flattens a value the lecturer was
never shown.
"""

import sys
from datetime import datetime, timedelta, timezone
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
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.services import criteria_service, unit_composition as uc
from app.services.rule_engine import (
    DEFAULT_THRESHOLD, THRESHOLD_FLOORS, calculate_badness,
)

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

engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                       poolclass=StaticPool)
Base.metadata.create_all(engine)
db = Session(engine)

lecturer = User(email="l@example.com", full_name="Lecturer", hashed_password="x",
                role=UserRole.LECTURER, is_active=True)
other = User(email="o@example.com", full_name="Other Lecturer", hashed_password="x",
             role=UserRole.LECTURER, is_active=True)
admin = User(email="a@example.com", full_name="Admin", hashed_password="x",
             role=UserRole.ADMIN, is_active=True)
db.add_all([lecturer, other, admin])
db.flush()

_unit_seq = 0


def make_unit(code: str = "ICT729", owner: User | None = None) -> Unit:
    """A created unit: attendance and Moodle seeded, no shape yet."""
    global _unit_seq
    _unit_seq += 1
    unit = Unit(unit_code=code, unit_name="Test Unit", year=2026,
                teaching_period=f"S{_unit_seq}",
                lecturer_id=(owner or lecturer).id,
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
    s = Student(name=f"Student {_student_seq}", student_number=f"T4{_student_seq:05d}",
                email=f"t4s{_student_seq}@example.com")
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


def add_verdict(unit: Unit, created_at: datetime, week: int = 8) -> FinalVerdict:
    student = make_student()
    scores = []
    for engine_name in ("rule_based", "ml_model"):
        score = RiskScore(student_id=student.id, unit_id=unit.id, checkpoint_week=week,
                          source=engine_name, risk_score=0.4, risk_level="low_risk")
        db.add(score)
        scores.append(score)
    db.flush()
    verdict = FinalVerdict(student_id=student.id, unit_id=unit.id, checkpoint_week=week,
                           rule_score_id=scores[0].id, ml_score_id=scores[1].id,
                           final_tier="low_risk", requires_review=False,
                           created_at=created_at.replace(tzinfo=None))
    db.add(verdict)
    db.flush()
    return verdict


def item(name, kind, pct, id=None):
    return {"id": id, "name": name, "kind": kind, "percentage": pct}


def rows(unit: Unit, category) -> list[Criteria]:
    return (db.query(Criteria)
            .filter(Criteria.unit_id == unit.id, Criteria.category == category,
                    Criteria.enabled.is_(True))
            .order_by(Criteria.id).all())


def refused(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        return None
    except ValueError as exc:
        return str(exc)


QUIZ = AssessmentKind.QUIZ.value
ASSIGN = AssessmentKind.ASSIGNMENT.value


# ---------------------------------------------------------------------

heading("The floors come from D1, not from a second copy")
# Two copies of a floor is two places for it to be wrong, and the copy
# nobody re-checks is the one that drifts.
check("assessment floor is 45", THRESHOLD_FLOORS["assessment"] == 45.0)
check("tutorial floor is 40", THRESHOLD_FLOORS["weekly_tut"] == 40.0)
check("the default is 50", DEFAULT_THRESHOLD == 50.0)
check("unit_composition defines NO floor of its own", not any(
    name for name in dir(uc)
    if "FLOOR" in name.upper()),
    "floors must be read from rule_engine, never restated")
check("the adjustable categories are assessment + weekly_tut",
      {uc._kind_value(c) for c in uc.ADJUSTABLE_CATEGORIES}
      == {"assessment", "weekly_tut"})
check("...and they are exactly D1's floored categories",
      {uc._kind_value(c) for c in uc.ADJUSTABLE_CATEGORIES}
      == set(THRESHOLD_FLOORS))

heading("The view reports one group per category, with real numbers")
u = make_unit("ICT710")
uc.replace_unit_shape(db, u, [
    item("Quiz 1", QUIZ, 20), item("Report", ASSIGN, 40),
], tutorials_enabled=True)
db.commit()

view = uc.lecturer_threshold_view(db, u)
check("the coordinator's shape is carried unchanged",
      view["total_percentage"] == 70.0, str(view["total_percentage"]))
check("both assessments are listed", len(view["assessments"]) == 2)
check("their pass marks are derived", [r["pass_mark"] for r in view["assessments"]]
      == [10.0, 20.0], str([r["pass_mark"] for r in view["assessments"]]))
check("the tutorial's pass mark is a completion percentage",
      view["tutorial"]["pass_mark"] == 50.0)

groups = view["thresholds"]
check("there are exactly two groups", set(groups) == {"assessment", "weekly_tut"})
check("assessments start at the 50 default", groups["assessment"]["value"] == 50.0)
check("the assessment slider writes to BOTH items",
      groups["assessment"]["applies_to"] == 2)
check("its floor is 45", groups["assessment"]["floor"] == 45.0)
check("the tutorial floor is 40", groups["weekly_tut"]["floor"] == 40.0)
check("the tutorial slider writes to one row",
      groups["weekly_tut"]["applies_to"] == 1)
check("nothing is mixed yet", groups["assessment"]["mixed"] is False)
check("the item names are named so the form can say what moves",
      groups["assessment"]["item_names"] == ["Quiz 1", "Report"],
      str(groups["assessment"]["item_names"]))
check("attendance and Moodle get NO group",
      "attendance" not in groups and "moodle" not in groups)
check("...but are still stated as automatic", len(view["automatic"]) == 2)

heading("MIXED bars are reported, never silently flattened on read")
# D1's per-item endpoint has always been able to leave two assessments
# on different bars. A slider that rendered the first row's value would
# show 50 for a unit whose second assessment sits at 46, and the first
# drag would flatten the 46 without ever displaying it.
rows(u, Cat.ASSESSMENT)[1].threshold = 46.0
db.flush()
mixed = uc.threshold_group(db, u, Cat.ASSESSMENT)
check("value is None when the rows disagree", mixed["value"] is None, str(mixed))
check("mixed is True", mixed["mixed"] is True)
check("both values are reported so the form can name them",
      mixed["values"] == [46.0, 50.0], str(mixed["values"]))
check("the slider is still adjustable", mixed["adjustable"] is True)
# Saving flattens - that is what ONE slider means - but only after the
# lecturer has been told what they are flattening.
uc.apply_threshold_changes(db, u, {"assessment": 47.0})
db.commit()
flat = uc.threshold_group(db, u, Cat.ASSESSMENT)
check("a save flattens the group", flat["value"] == 47.0 and flat["mixed"] is False,
      str(flat))
check("...to every row in it",
      [r.threshold for r in rows(u, Cat.ASSESSMENT)] == [47.0, 47.0])

heading("A category the unit does not have gets no slider")
blank = make_unit("ICT711")
blank_view = uc.lecturer_threshold_view(db, blank)
check("a unit with no assessments reports applies_to 0",
      blank_view["thresholds"]["assessment"]["applies_to"] == 0)
check("...and is not adjustable",
      blank_view["thresholds"]["assessment"]["adjustable"] is False,
      "a control that writes nothing reports success and changes nothing")
check("...and has no value to show",
      blank_view["thresholds"]["assessment"]["value"] is None)
# ...and writing to it is an honest refusal rather than a silent no-op.
err = refused(uc.apply_threshold_changes, db, blank, {"assessment": 46.0})
check("writing to an absent category is refused", err is not None)
check("...and the message says who can add one",
      "coordinator" in (err or "").lower(), str(err))

heading("THE ONE THAT MATTERS: the shape lock does NOT cover the bar")
# A unit is locked exactly when marks exist or an analysis has run -
# which is exactly when a lecturer decides the bar is wrong. A shared
# lock would make the slider editable only where it changes nothing.
locked = make_unit("ICT712")
uc.replace_unit_shape(db, locked, [item("Quiz 1", QUIZ, 20)], tutorials_enabled=True)
db.commit()
qrow = rows(locked, Cat.ASSESSMENT)[0]
add_event(locked, qrow, 15.0)
add_verdict(locked, NOW - timedelta(days=2))
db.commit()

check("the unit IS locked", uc.shape_lock_state(db, locked)["state"] == "locked")
shape_err = None
try:
    uc.replace_unit_shape(db, locked, [item("Quiz 1", QUIZ, 15)], True)
except uc.ShapeLockedError as exc:
    db.rollback()
    shape_err = str(exc)
check("a shape change is still refused with a ShapeLockedError",
      shape_err is not None, str(shape_err))

after = uc.apply_threshold_changes(db, locked, {"assessment": 45.0})
db.commit()
check("but the BAR moves on the same locked unit",
      after["thresholds"]["assessment"]["value"] == 45.0, str(after["thresholds"]))
check("...and it really reached the row",
      rows(locked, Cat.ASSESSMENT)[0].threshold == 45.0)
check("the unit is STILL locked afterwards",
      uc.shape_lock_state(db, locked)["state"] == "locked",
      "moving a bar is not an unlock")

heading("...but it DOES mark the analyses stale")
# calculate_badness reads the bar directly, so every rule-based score in
# the unit just changed. Verdicts computed before the move were scored
# against a bar that no longer exists - which is T1's definition of
# stale, reused rather than reinvented.
check("badness really depends on the bar",
      calculate_badness(44.0, 50.0) != calculate_badness(44.0, 45.0),
      f"{calculate_badness(44.0, 50.0)} vs {calculate_badness(44.0, 45.0)}")
check("criteria_updated_at was bumped", locked.criteria_updated_at is not None)
summary = uc.stale_verdict_summary(db, locked)
check("the earlier verdict is now stale", summary["stale_count"] == 1, str(summary))

from app.services import report_service  # noqa: E402
caveats = report_service._caveats(
    criteria=[], buckets=["safe"], incomplete_count=0,
    last_analysed_at=NOW, intervention_available=True, now=NOW, stale=summary)
check("the report says so, through T1's existing caveat",
      any("criteria were last changed" in c for c in caveats), str(caveats))
check("...and tells the lecturer to re-run",
      any("re-run" in c.lower() for c in caveats))

heading("A bar change does NOT consume an admin's unlock window")
# The window was opened for a SHAPE change. Spending it on a lecturer
# lowering a bar would close the door on the coordinator who asked for
# it - the same argument T1 makes for a rename.
uc.unlock_shape(db, locked, "ICT712", actor_id=admin.id, now=NOW)
db.commit()
check("the window is open", locked.criteria_unlocked_at is not None)
uc.apply_threshold_changes(db, locked, {"assessment": 46.0})
db.commit()
check("the window is STILL open after a bar change",
      locked.criteria_unlocked_at is not None,
      "record_threshold_write must not clear it")
check("...and who opened it is still recorded",
      locked.criteria_unlocked_by == admin.id)
# A real shape change still closes it.
uc.replace_unit_shape(db, locked, [item("Quiz 1", QUIZ, 15, id=qrow.id)], True)
db.commit()
check("a shape change still closes it", locked.criteria_unlocked_at is None)

heading("Saving an unchanged bar writes nothing and marks nothing stale")
# The page GETs the view and PATCHes it back, so a lecturer who opens a
# unit and presses Save has sent the stored values. Bumping the
# timestamp there would mark a whole cohort's results stale for a
# no-op.
idem = make_unit("ICT713")
uc.replace_unit_shape(db, idem, [item("Quiz 1", QUIZ, 20)], tutorials_enabled=True)
db.commit()
uc.apply_threshold_changes(db, idem, {"assessment": 48.0, "weekly_tut": 42.0})
db.commit()
stamp = idem.criteria_updated_at
check("the first save stamped it", stamp is not None)
uc.apply_threshold_changes(db, idem, {"assessment": 48.0, "weekly_tut": 42.0})
db.commit()
check("re-saving the SAME values did not move the timestamp",
      idem.criteria_updated_at == stamp)
check("an empty payload is a no-op, not an error",
      uc.apply_threshold_changes(db, idem, {})["thresholds"]["assessment"]["value"]
      == 48.0)
check("...and a None entry means 'leave this one alone'",
      uc.apply_threshold_changes(
          db, idem, {"assessment": None, "weekly_tut": 41.0}
      )["thresholds"]["assessment"]["value"] == 48.0)
db.commit()
check("...while the other one moved", rows(idem, Cat.WEEKLY_TUT)[0].threshold == 41.0)

heading("D1's floors are enforced, by calling D1 rather than restating it")
check("41% on an assessment is refused (floor 45)",
      refused(uc.apply_threshold_changes, db, idem, {"assessment": 41.0}) is not None)
check("45% exactly is allowed - the floor is inclusive",
      refused(uc.apply_threshold_changes, db, idem, {"assessment": 45.0}) is None)
db.commit()
check("39% on tutorials is refused (floor 40)",
      refused(uc.apply_threshold_changes, db, idem, {"weekly_tut": 39.0}) is not None)
check("40% exactly is allowed",
      refused(uc.apply_threshold_changes, db, idem, {"weekly_tut": 40.0}) is None)
db.commit()
check("51% is refused - the bar is LOWER-ONLY",
      refused(uc.apply_threshold_changes, db, idem, {"assessment": 51.0}) is not None,
      "a lecturer quietly making their unit harder to pass is the other risk")
check("...and the refusal names the 50% default",
      "50" in (refused(uc.apply_threshold_changes, db, idem,
                       {"assessment": 51.0}) or ""))
check("attendance is refused outright, not ignored",
      refused(uc.apply_threshold_changes, db, idem, {"attendance": 40.0}) is not None)
check("...and the message says it is fixed",
      "fixed" in (refused(uc.apply_threshold_changes, db, idem,
                          {"attendance": 40.0}) or "").lower())
check("a refused write left every row untouched",
      rows(idem, Cat.ASSESSMENT)[0].threshold == 45.0,
      "validation runs before the first setattr")

heading("The per-item PATCH is now threshold-only (the back door)")
# Before T4 a lecturer could re-weight an assessment to 90%, or flip its
# category, through this endpoint - and no composition rule (max 3
# items, 20% quiz cap, 100% budget) would ever have seen it, because
# those live in the coordinator's admin PUT.
guard = criteria_service.assert_lecturer_edits_only_threshold
check("threshold alone is allowed", refused(guard, {"threshold": 46.0}) is None)
check("an empty patch is allowed", refused(guard, {}) is None)
for field in ("weight", "max_score", "category", "sequence_number", "enabled", "name"):
    check(f"{field} is refused", refused(guard, {field: 1}) is not None)
message = refused(guard, {"weight": 0.9, "max_score": 90})
check("the message lists every refused field",
      "weight" in (message or "").lower()
      and "max score" in (message or "").lower(), str(message))
check("...and says who does own them",
      "coordinator" in (message or "").lower(), str(message))
check("the guard is keyed on a named set, not a hard-coded list",
      criteria_service.LECTURER_EDITABLE_FIELDS == frozenset({"threshold"}))

heading("`kind` finally reaches the lecturer-facing schema")
# Standing item: T2 added the column and the admin endpoint but not
# CriteriaOut, so the overview tab, the import wizard and the manual
# entry form could not tell a quiz from an assignment.
from app.schemas.criteria import CriteriaOut  # noqa: E402
check("CriteriaOut has a `kind` field", "kind" in CriteriaOut.model_fields)
check("...and it is optional", CriteriaOut.model_fields["kind"].is_required() is False)
sample = CriteriaOut.model_validate(rows(idem, Cat.ASSESSMENT)[0])
check("a quiz serialises as quiz", sample.kind == AssessmentKind.QUIZ, str(sample.kind))
tut_out = CriteriaOut.model_validate(rows(idem, Cat.WEEKLY_TUT)[0])
check("a tutorial has no kind", tut_out.kind is None)

heading("LIVE HTTP: the lecturer endpoints over the wire")
from fastapi import FastAPI                                    # noqa: E402
from fastapi.testclient import TestClient                      # noqa: E402
from app.api.routes.criteria import router as criteria_router  # noqa: E402
from app.core.dependencies import get_current_user             # noqa: E402
from app.database import get_db                                # noqa: E402

api = FastAPI()
api.include_router(criteria_router)
acting_as = {"user": lecturer}
api.dependency_overrides[get_db] = lambda: db
api.dependency_overrides[get_current_user] = lambda: acting_as["user"]
client = TestClient(api)

http_unit = make_unit("ICT800")
uc.replace_unit_shape(db, http_unit, [
    item("Quiz 1", QUIZ, 20), item("Report", ASSIGN, 45),
], tutorials_enabled=True)
db.commit()
base = f"/units/{http_unit.id}/criteria"

got = client.get(f"{base}/shape")
check("GET /shape returns 200, not a 422 about an integer",
      got.status_code == 200, got.text)
body = got.json()
check("...carrying the coordinator's items", len(body["assessments"]) == 2)
check("...their pass marks", body["assessments"][0]["pass_mark"] == 10.0, got.text)
check("...their kinds", body["assessments"][0]["kind"] == "quiz")
check("...the lock state", body["lock"]["state"] == "draft")
check("...and both sliders", set(body["thresholds"]) == {"assessment", "weekly_tut"})

patched = client.patch(f"{base}/thresholds", json={"assessment": 46})
check("PATCH /thresholds returns 200", patched.status_code == 200, patched.text)
check("...with the new value echoed",
      patched.json()["thresholds"]["assessment"]["value"] == 46.0, patched.text)
check("...and the derived pass mark recomputed",
      patched.json()["assessments"][0]["pass_mark"] == 9.2,
      "20 marks * 46% - the read model, not a stored column")

low = client.patch(f"{base}/thresholds", json={"assessment": 30})
check("below the floor is 400", low.status_code == 400, low.text)
check("the 400 names the floor", "45" in low.json()["detail"], low.text)

high = client.patch(f"{base}/thresholds", json={"assessment": 60})
check("above the default is 400", high.status_code == 400, high.text)

fixed = client.patch(f"{base}/thresholds", json={"attendance": 40})
check("a fixed category is 422 - the field does not exist here",
      fixed.status_code == 422, f"{fixed.status_code} {fixed.text}")

junk = client.patch(f"{base}/thresholds", json={"weight": 0.9})
check("a shape field is 422 - this is not an edit endpoint",
      junk.status_code == 422, f"{junk.status_code} {junk.text}")

check("the bar survived every refusal",
      client.get(f"{base}/shape").json()["thresholds"]["assessment"]["value"] == 46.0)

both = client.patch(f"{base}/thresholds", json={"assessment": 45, "weekly_tut": 42})
check("both sliders save in one call", both.status_code == 200, both.text)
check("...assessment moved", both.json()["thresholds"]["assessment"]["value"] == 45.0)
check("...and tutorials moved", both.json()["thresholds"]["weekly_tut"]["value"] == 42.0)

# The per-item route, over the wire.
target = rows(http_unit, Cat.ASSESSMENT)[0]
ok_patch = client.patch(f"{base}/{target.id}", json={"threshold": 47})
check("a per-item threshold PATCH still works", ok_patch.status_code == 200,
      ok_patch.text)
bad_patch = client.patch(f"{base}/{target.id}", json={"weight": 0.9})
check("a per-item weight PATCH is 400", bad_patch.status_code == 400, bad_patch.text)
name_patch = client.patch(f"{base}/{target.id}", json={"name": "Renamed"})
check("a per-item rename is 400 - names are the coordinator's now",
      name_patch.status_code == 400, name_patch.text)

# Tenant isolation. Widening a read is exactly how a cross-tenant leak
# gets introduced, and T5 widens more of them.
acting_as["user"] = other
check("another lecturer cannot read the shape (403)",
      client.get(f"{base}/shape").status_code == 403)
check("another lecturer cannot move the bar (403)",
      client.patch(f"{base}/thresholds", json={"assessment": 45}).status_code == 403)
acting_as["user"] = admin
check("an admin CAN read the shape they configured",
      client.get(f"{base}/shape").status_code == 200)
check("...but is not the one who moves the bar (403)",
      client.patch(f"{base}/thresholds", json={"assessment": 45}).status_code == 403,
      "widening this is T5's job, with its isolation retest attached")
acting_as["user"] = lecturer
check("an unknown unit is 404",
      client.get("/units/999999/criteria/shape").status_code == 404)

heading("The routes are wired, and in the right order")
route_source = Path("app/api/routes/criteria.py").read_text()
check("the shape endpoint exists", '"/shape"' in route_source)
check("the thresholds endpoint exists", '"/thresholds"' in route_source)
# FastAPI matches in declaration order and /{criteria_id} is typed int,
# so a literal declared after it 422s rather than falling through.
check("both are declared BEFORE /{criteria_id}",
      route_source.index('"/shape"') < route_source.index('"/{criteria_id}"')
      and route_source.index('"/thresholds"')
      < route_source.index('"/{criteria_id}"'))
check("the per-item PATCH calls the field guard",
      "assert_lecturer_edits_only_threshold" in route_source)
check("...before the D1 guard", route_source.index(
    "assert_lecturer_edits_only_threshold") < route_source.index(
    "assert_lecturer_may_update"))
check("the update route no longer CALLS the shape lock",
      "unit_composition.assert_may_update_criteria(" not in route_source,
      "a guard that can never fire is case ten")
check("...and records staleness instead",
      "record_threshold_write" in route_source)

import main as app_main                                        # noqa: E402
paths = app_main.app.openapi()["paths"]
check("the full app exposes GET /units/{unit_id}/criteria/shape",
      "get" in paths.get("/units/{unit_id}/criteria/shape", {}),
      str(sorted(p for p in paths if "criteria" in p)))
check("...and PATCH /units/{unit_id}/criteria/thresholds",
      "patch" in paths.get("/units/{unit_id}/criteria/thresholds", {}))
check("the admin shape endpoint is untouched",
      "put" in paths.get("/admin/units/{unit_id}/criteria", {}))

heading("No migration was needed, and that is the point")
# The bar has always been a column. T4 adds an endpoint and a screen,
# not a schema change - which is why nothing here has to be reversible.
check("threshold is an existing column", hasattr(Criteria, "threshold"))
check("no T4 migration was added", not any(
    "t4" in f.name.lower() or "threshold_bar" in f.name.lower()
    for f in Path("alembic/versions").glob("*.py")))
from alembic.config import Config                              # noqa: E402
from alembic.script import ScriptDirectory                     # noqa: E402
heads = ScriptDirectory.from_config(Config("alembic.ini")).get_heads()
check("alembic still has the single T2 head",
      list(heads) == ["a6b7c8d9e0f1"], str(heads))

print("\n" + "=" * 60)
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections)")