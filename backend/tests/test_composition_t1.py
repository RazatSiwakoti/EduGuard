"""
Section T1 verification - the two lives of a unit's shape.

Run from `backend/`:

    PYTHONPATH=. python3 tests/test_composition_t1.py

The section that carries the most weight is [3]: an attendance import
must NOT lock a unit. Attendance rows are `AssessmentEvent` rows exactly
like a quiz mark, so the obvious implementation - "any ingested data
locks the shape" - freezes a unit the moment a lecturer uploads week-1
attendance, which happens before the coordinator has entered a single
assessment. The unit would arrive at configuration time already locked.

Section [10] is the other one worth reading: a rename must not consume
the one-shot unlock window, or an admin who unlocks a unit and fixes a
typo finds the door shut behind them.
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
from app.models.enums import CriteriaCategory as Cat, EventSource, UserRole
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.services import unit_composition
from app.services.unit_composition import ShapeLockedError

NOW = datetime(2026, 8, 27, 9, 0, tzinfo=timezone.utc)

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

def build_db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


db = build_db()

lecturer = User(
    email="l@example.com", full_name="Lecturer", hashed_password="x",
    role=UserRole.LECTURER, is_active=True,
)
admin = User(
    email="a@example.com", full_name="Admin", hashed_password="x",
    role=UserRole.ADMIN, is_active=True,
)
db.add_all([lecturer, admin])
db.flush()

_unit_seq = 0


def make_unit(code: str = "ICT729") -> Unit:
    """A fresh unit with the four seeded criteria, in DRAFT."""
    global _unit_seq
    _unit_seq += 1
    unit = Unit(
        unit_code=code, unit_name="Test Unit", year=2026,
        teaching_period=f"S{_unit_seq}", lecturer_id=lecturer.id,
        is_active=True, status="ASSIGNED",
    )
    db.add(unit)
    db.flush()

    for name, category, threshold, weight in (
        ("Attendance", Cat.ATTENDANCE, 50.0, 0.5),
        ("Moodle", Cat.MOODLE, 10.0, 0.05),
        ("Weekly Tutorials", Cat.WEEKLY_TUT, 50.0, 0.10),
        ("Quiz 1", Cat.ASSESSMENT, 50.0, 0.20),
    ):
        db.add(Criteria(
            unit_id=unit.id, name=name, category=category,
            threshold=threshold, weight=weight, max_score=100.0, enabled=True,
        ))
    db.flush()
    return unit


def criterion(unit: Unit, category) -> Criteria:
    return (
        db.query(Criteria)
        .filter(Criteria.unit_id == unit.id, Criteria.category == category)
        .first()
    )


_student_seq = 0


def make_student() -> Student:
    global _student_seq
    _student_seq += 1
    student = Student(
        name=f"Student {_student_seq}",
        student_number=f"S{_student_seq:05d}",
        email=f"s{_student_seq}@example.com",
    )
    db.add(student)
    db.flush()
    return student


def add_event(unit: Unit, category, score: float = 70.0) -> AssessmentEvent:
    event = AssessmentEvent(
        student_id=make_student().id,
        unit_id=unit.id,
        criteria_id=criterion(unit, category).id,
        score=score,
        source=EventSource.BULK_UPLOAD,
        created_by=lecturer.id,
        date=NOW.replace(tzinfo=None),
    )
    db.add(event)
    db.flush()
    return event


def add_verdict(unit: Unit, created_at: datetime, week: int = 8) -> FinalVerdict:
    student = make_student()
    scores = []
    for engine_name in ("rule_based", "ml_model"):
        score = RiskScore(
            student_id=student.id, unit_id=unit.id, checkpoint_week=week,
            source=engine_name, risk_score=0.4, risk_level="low_risk",
        )
        db.add(score)
        scores.append(score)
    db.flush()

    verdict = FinalVerdict(
        student_id=student.id, unit_id=unit.id, checkpoint_week=week,
        rule_score_id=scores[0].id, ml_score_id=scores[1].id,
        final_tier="low_risk", requires_review=False,
        created_at=created_at.replace(tzinfo=None),
    )
    db.add(verdict)
    db.flush()
    return verdict


def state(unit: Unit) -> dict:
    return unit_composition.shape_lock_state(db, unit)


def refuses(fn, *args, **kwargs) -> str | None:
    """The refusal message, or None if it was allowed through."""
    try:
        fn(*args, **kwargs)
        return None
    except ShapeLockedError as exc:
        return str(exc)


# ---------------------------------------------------------------------

heading("A brand-new unit is in DRAFT")
draft = make_unit()
check("state is draft", state(draft)["state"] == "draft", str(state(draft)))
check("locked is False", state(draft)["locked"] is False)
check("no reasons are given", state(draft)["reasons"] == [])
check("a criterion may be added", refuses(
    unit_composition.assert_may_create_criteria, db, draft) is None)
check("a criterion may be changed", refuses(
    unit_composition.assert_may_update_criteria, db, draft,
    criterion(draft, Cat.ASSESSMENT), {"weight": 0.25}) is None)
check("a criterion may be removed", refuses(
    unit_composition.assert_may_delete_criteria, db, draft) is None)
check("criteria_updated_at starts NULL - nothing is stale on day one",
      draft.criteria_updated_at is None)

heading("Assessment data LOCKS the unit")
locked_unit = make_unit()
add_event(locked_unit, Cat.ASSESSMENT, 68.0)
check("state is locked", state(locked_unit)["state"] == "locked")
check("the reason names the recorded results",
      "result" in " ".join(state(locked_unit)["reasons"]),
      str(state(locked_unit)["reasons"]))
check("adding is refused", refuses(
    unit_composition.assert_may_create_criteria, db, locked_unit) is not None)
check("changing a weight is refused", refuses(
    unit_composition.assert_may_update_criteria, db, locked_unit,
    criterion(locked_unit, Cat.ASSESSMENT), {"weight": 0.25}) is not None)
check("removing is refused", refuses(
    unit_composition.assert_may_delete_criteria, db, locked_unit) is not None)
check("the refusal points at the unlock path",
      "unlock" in (refuses(unit_composition.assert_may_create_criteria,
                           db, locked_unit) or "").lower())

heading("Tutorial data locks it too")
tut_unit = make_unit()
add_event(tut_unit, Cat.WEEKLY_TUT, 80.0)
check("a weekly-tutorial result locks the unit",
      state(tut_unit)["state"] == "locked")

heading("ATTENDANCE DOES NOT LOCK IT - the one that matters")
# Attendance rows are AssessmentEvent rows exactly like a quiz mark. The
# obvious rule - "any ingested data locks the shape" - would freeze this
# unit the moment a lecturer uploaded week-1 attendance, BEFORE the
# coordinator had entered a single assessment.
att_unit = make_unit()
add_event(att_unit, Cat.ATTENDANCE, 90.0)
add_event(att_unit, Cat.ATTENDANCE, 45.0)
check("two attendance imports leave the unit in DRAFT",
      state(att_unit)["state"] == "draft", str(state(att_unit)))
check("the locking-event count ignores them",
      state(att_unit)["locking_event_count"] == 0)
check("the coordinator can still configure the unit", refuses(
    unit_composition.assert_may_create_criteria, db, att_unit) is None)

heading("MOODLE DOES NOT LOCK IT EITHER")
moodle_unit = make_unit()
add_event(moodle_unit, Cat.MOODLE, 14.0)
check("a Moodle import leaves the unit in DRAFT",
      state(moodle_unit)["state"] == "draft", str(state(moodle_unit)))
check("attendance AND Moodle together still leave it draft",
      (lambda u: (add_event(u, Cat.ATTENDANCE, 60.0),
                  state(u)["state"])[1])(moodle_unit) == "draft")
# ...and the moment one real assessment mark arrives, it locks.
add_event(moodle_unit, Cat.ASSESSMENT, 55.0)
check("one assessment mark on the same unit locks it immediately",
      state(moodle_unit)["state"] == "locked")

heading("A verdict locks the unit even with no marks recorded")
# An analysis can run off attendance and Moodle alone. Once it has
# produced verdicts, the shape those verdicts were scored against is
# load-bearing whether or not an assessment mark exists.
verdict_unit = make_unit()
add_event(verdict_unit, Cat.ATTENDANCE, 30.0)
check("still draft before the analysis", state(verdict_unit)["state"] == "draft")
add_verdict(verdict_unit, NOW - timedelta(days=1))
check("a FinalVerdict locks it", state(verdict_unit)["state"] == "locked")
check("no assessment events were needed",
      state(verdict_unit)["locking_event_count"] == 0)
check("the reason mentions the analysis",
      "analysis" in " ".join(state(verdict_unit)["reasons"]).lower())

heading("A RENAME survives the lock - a label is not a rule")
renamable = criterion(locked_unit, Cat.ASSESSMENT)
check("renaming a criterion on a locked unit is allowed", refuses(
    unit_composition.assert_may_update_criteria, db, locked_unit,
    renamable, {"name": "Week 4 Quiz"}) is None)
check("rename + weight together is refused", refuses(
    unit_composition.assert_may_update_criteria, db, locked_unit,
    renamable, {"name": "Week 4 Quiz", "weight": 0.3}) is not None,
    "the weight is the shape change; the name does not excuse it")
# A client that PATCHes the whole object back has changed nothing.
check("a no-op PATCH echoing stored values is allowed", refuses(
    unit_composition.assert_may_update_criteria, db, locked_unit, renamable,
    {"name": renamable.name, "weight": renamable.weight,
     "threshold": renamable.threshold}) is None)
check("is_shape_change() treats name as a label",
      unit_composition.is_shape_change({"name": "x"}) is False)
check("...and anything else as shape", all(
    unit_composition.is_shape_change({field: 1})
    for field in ("weight", "threshold", "max_score", "category",
                  "enabled", "sequence_number")))
# A column added to Criteria later must default to LOCKED, not exempt.
check("an unknown future field is treated as a shape change",
      unit_composition.is_shape_change({"some_future_column": 1}) is True)

heading("Unlock: the typed confirmation")


def unlock_error(unit, typed) -> str | None:
    try:
        unit_composition.unlock_shape(db, unit, typed, actor_id=admin.id, now=NOW)
        return None
    except ValueError as exc:
        return str(exc)


check("the wrong unit code is refused",
      unlock_error(locked_unit, "ICT999") is not None)
check("an empty confirmation is refused",
      unlock_error(locked_unit, "") is not None)
check("the message says which code was expected",
      locked_unit.unit_code in (unlock_error(locked_unit, "nope") or ""))
check("the unit is STILL locked after a failed confirmation",
      state(locked_unit)["state"] == "locked")
# Case and whitespace prove nothing about intent.
check("lower case with whitespace is accepted",
      unlock_error(locked_unit, "  ict729 ") is None)
check("the unit is now effectively draft",
      state(locked_unit)["state"] == "draft", str(state(locked_unit)))
check("...but it is still 'lockable' - the data did not go away",
      state(locked_unit)["lockable"] is True)
check("unlock_active is reported so the UI can say so",
      state(locked_unit)["unlock_active"] is True)
check("the actor is recorded", locked_unit.criteria_unlocked_by == admin.id)
check("unlocking twice is idempotent, not an error",
      unlock_error(locked_unit, "ICT729") is None)
# Unlocking must not, by itself, invalidate a single result.
check("unlocking did NOT touch criteria_updated_at",
      locked_unit.criteria_updated_at is None,
      "staleness lands on the save, not on opening the door")

heading("Unlock is ONE-SHOT and a rename does not consume it")
# The window exists to permit one shape change. A coordinator who
# unlocks a unit, fixes a typo in a label and finds the door shut behind
# them would reasonably conclude the feature is broken.
unit_composition.record_criteria_write(locked_unit, shape_changed=False)
check("a rename leaves the unlock window open",
      locked_unit.criteria_unlocked_at is not None)
check("a rename does not bump criteria_updated_at",
      locked_unit.criteria_updated_at is None)

unit_composition.record_criteria_write(locked_unit, shape_changed=True, now=NOW)
check("a real save closes the window",
      locked_unit.criteria_unlocked_at is None)
check("...and clears who opened it",
      locked_unit.criteria_unlocked_by is None)
check("...and stamps criteria_updated_at",
      locked_unit.criteria_updated_at is not None)
check("the unit is locked again immediately",
      state(locked_unit)["state"] == "locked", str(state(locked_unit)))
check("a second edit is refused without a new unlock", refuses(
    unit_composition.assert_may_create_criteria, db, locked_unit) is not None)

heading("Staleness is derived from the timestamp, never stored")
stale_unit = make_unit("ICT700")
old = add_verdict(stale_unit, NOW - timedelta(days=3))
check("nothing is stale while criteria_updated_at is NULL",
      unit_composition.stale_verdict_summary(db, stale_unit)["stale_count"] == 0,
      "a NULL must not be read as 'changed at the epoch'")

unit_composition.record_criteria_write(stale_unit, now=NOW - timedelta(days=1))
summary = unit_composition.stale_verdict_summary(db, stale_unit)
check("a verdict older than the change is stale", summary["stale_count"] == 1)
check("the student count is reported", summary["student_count"] == 1)

fresh = add_verdict(stale_unit, NOW)
summary = unit_composition.stale_verdict_summary(db, stale_unit)
check("a verdict newer than the change is NOT stale",
      summary["stale_count"] == 1, str(summary))
check("the total is both of them", summary["total_count"] == 2)
# A week-4 analysis going stale is not a caveat on a week-8 report.
add_verdict(stale_unit, NOW - timedelta(days=3), week=4)
check("staleness can be scoped to one checkpoint",
      unit_composition.stale_verdict_summary(
          db, stale_unit, checkpoint_week=4)["stale_count"] == 1)
check("...and week 8 is unaffected by it",
      unit_composition.stale_verdict_summary(
          db, stale_unit, checkpoint_week=8)["stale_count"] == 1)
check("a naive created_at does not blow up the comparison",
      isinstance(summary["stale_count"], int),
      "aware/naive mixing raises TypeError, and both are present here")
check("there is no is_stale COLUMN anywhere",
      not hasattr(FinalVerdict, "is_stale"),
      "derived at read time on purpose - a flag would drift")

heading("Unlock preview states the cost before it is paid")
preview = unit_composition.unlock_preview(db, stale_unit)
check("the preview names the unit code", preview["unit_code"] == "ICT700")
check("already-stale results are counted separately",
      preview["verdicts_already_stale"] == 2, str(preview))
check("only still-valid results are quoted as the cost",
      preview["verdicts_currently_valid"] == 1, str(preview))
check("the students affected are counted", preview["students_affected"] == 3)
check("the sentence is about SAVING, not about unlocking",
      "saving" in preview["consequence"].lower(), preview["consequence"])
check("the preview carries the lock state too",
      preview["state"] in ("draft", "locked"))
# Re-invalidating something already invalid costs nothing; quoting the
# larger number would overstate the damage.
check("the cost is never the raw verdict count",
      preview["verdicts_currently_valid"] < preview["verdict_count"],
      str(preview))

heading("The report carries staleness as a caveat")
from app.services import report_service  # noqa: E402

caveats = report_service._caveats(
    criteria=[], buckets=["safe"], incomplete_count=0,
    last_analysed_at=NOW, intervention_available=True, now=NOW,
    stale={"stale_count": 3, "student_count": 2, "changed_at": NOW,
           "total_count": 5},
)
stale_line = next((c for c in caveats if "criteria were last changed" in c), None)
check("a stale-shape caveat is emitted", stale_line is not None, str(caveats))
check("it quotes the result count", "3 risk results" in (stale_line or ""))
check("it quotes the student count", "2 students" in (stale_line or ""))
check("it tells the reader what to do",
      "re-run" in (stale_line or "").lower())
check("no caveat when nothing is stale", not any(
    "criteria were last changed" in c for c in report_service._caveats(
        criteria=[], buckets=["safe"], incomplete_count=0,
        last_analysed_at=NOW, intervention_available=True, now=NOW,
        stale={"stale_count": 0, "student_count": 0, "changed_at": None,
               "total_count": 0})))
# The C-block suites call _caveats positionally with six arguments.
check("stale is optional - the C-block callers still work",
      isinstance(report_service._caveats(
          [], ["safe"], 0, NOW, True, NOW), list))
# Age and shape are different doubts: a shape change invalidates an
# analysis that ran five minutes ago just as thoroughly as an old one.
check("the stale caveat is separate from the 'ran N days ago' one",
      sum(1 for c in caveats if "days ago" in c) == 0
      or stale_line not in [c for c in caveats if "days ago" in c])

heading("The routes are actually wired")
route_source = Path("app/api/routes/criteria.py").read_text()
check("create calls the lock guard",
      "assert_may_create_criteria" in route_source)
check("update calls the lock guard",
      "assert_may_update_criteria" in route_source)
check("delete calls the lock guard",
      "assert_may_delete_criteria" in route_source)
check("every write path records the write",
      route_source.count("record_criteria_write") == 3)
check("the unlock endpoint exists", '"/unlock"' in route_source)
check("the preview endpoint exists", '"/unlock-preview"' in route_source)
check("the lock-state endpoint exists", '"/lock-state"' in route_source)
check("a lock refusal is 409, not 400",
      "HTTP_409_CONFLICT" in route_source,
      "400 means 'fix the value'; the value is fine, the unit is not")
# FastAPI matches in declaration order and `/{criteria_id}` is typed int,
# so a literal route declared after it returns 422, not a fallthrough.
check("literal routes are declared BEFORE /{criteria_id}",
      route_source.index('"/lock-state"') < route_source.index('"/{criteria_id}"'),
      "otherwise /lock-state is parsed as a criteria_id and 422s")
check("unlock-preview too",
      route_source.index('"/unlock-preview"')
      < route_source.index('"/{criteria_id}"'))
check("the report service asks for the staleness summary",
      "stale_verdict_summary" in
      Path("app/services/report_service.py").read_text())

heading("The app still boots with the new columns")
# Unit gained a SECOND foreign key to users.id. Without explicit
# `foreign_keys` on both sides of User.units, SQLAlchemy raises
# AmbiguousForeignKeysError at mapper configuration - i.e. the whole app
# fails to start, and every other suite in this project passes because
# none of them configure the User mapper.
from sqlalchemy.orm import configure_mappers  # noqa: E402

boot_error = None
try:
    configure_mappers()
except Exception as exc:                      # pragma: no cover
    boot_error = exc
check("all mappers configure cleanly", boot_error is None, str(boot_error))
check("a user's units still resolve through lecturer_id",
      [u.id for u in db.get(User, lecturer.id).units] != [])

heading("The migration matches the model")
migration = Path(
    "alembic/versions/f5a6b7c8d9e0_add_criteria_shape_lifecycle_to_units.py"
).read_text()
for column in ("criteria_updated_at", "criteria_unlocked_at",
               "criteria_unlocked_by"):
    check(f"{column} is added", f'"{column}"' in migration)
    check(f"{column} exists on the model", hasattr(Unit, column))
check("it follows D1's migration", 'down_revision = "e4f5a6b7c8d9"' in migration)
check("nothing is back-filled",
      "UPDATE units" not in migration,
      "back-filling criteria_updated_at would mark every result stale")
check("the FK constraint is NAMED so downgrade can drop it",
      "fk_units_criteria_unlocked_by_users" in migration)
check("downgrade actually reverses it",
      migration.split("def downgrade")[1].count("drop_column") == 3)

heading("LIVE HTTP: the endpoints behave over the wire")
# Grepping the route file proves the calls are written. It does not prove
# FastAPI routes to them, that the status codes are what the frontend
# will see, or that /lock-state is not parsed as a criteria_id. Only a
# real request does that, so the routes are mounted on a throwaway app
# with the auth dependency overridden.
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
db.commit()
base = f"/units/{http_unit.id}/criteria"

response = client.get(f"{base}/lock-state")
check("GET /lock-state returns 200, not a 422 about an integer",
      response.status_code == 200, response.text)
check("...and reports draft", response.json()["state"] == "draft",
      response.text)

created = client.post(base, json={
    "name": "Quiz 2", "weight": 0.2, "threshold": 50.0,
    "max_score": 20.0, "category": "assessment", "sequence_number": 2,
})
check("a criterion can be created while draft",
      created.status_code == 201, created.text)
check("the write stamped criteria_updated_at",
      db.get(Unit, http_unit.id).criteria_updated_at is not None)

# Now lock it with a real assessment mark.
add_event(http_unit, Cat.ASSESSMENT, 61.0)
db.commit()
check("GET /lock-state now reports locked",
      client.get(f"{base}/lock-state").json()["state"] == "locked")

blocked = client.post(base, json={
    "name": "Quiz 3", "weight": 0.1, "threshold": 50.0,
    "max_score": 10.0, "category": "assessment", "sequence_number": 3,
})
check("creating on a locked unit returns 409",
      blocked.status_code == 409, f"{blocked.status_code} {blocked.text}")
check("the 409 detail explains why",
      "locked" in blocked.json()["detail"].lower())

target = criterion(http_unit, Cat.ASSESSMENT)
weight_patch = client.patch(f"{base}/{target.id}", json={"weight": 0.35})
check("changing a weight on a locked unit returns 409",
      weight_patch.status_code == 409, weight_patch.text)

rename = client.patch(f"{base}/{target.id}", json={"name": "Renamed Quiz"})
check("renaming on a locked unit still returns 200",
      rename.status_code == 200, rename.text)

# D1's rules must still produce 400, not 409 - the frontend distinguishes
# "fix this number" from "this unit is locked" by the status code alone.
acting_as["user"] = admin
client.post(f"{base}/unlock", json={"unit_code": "ICT800"})
acting_as["user"] = lecturer
too_low = client.patch(f"{base}/{target.id}", json={"threshold": 10.0})
check("a D1 floor breach is still 400, not 409",
      too_low.status_code == 400, f"{too_low.status_code} {too_low.text}")

acting_as["user"] = lecturer
check("a lecturer cannot unlock (403)",
      client.post(f"{base}/unlock", json={"unit_code": "ICT800"}
                  ).status_code == 403)
check("a lecturer cannot see the preview (403)",
      client.get(f"{base}/unlock-preview").status_code == 403)

acting_as["user"] = admin
check("GET /unlock-preview returns 200 for an admin",
      client.get(f"{base}/unlock-preview").status_code == 200)
wrong = client.post(f"{base}/unlock", json={"unit_code": "WRONG"})
check("a wrong typed code is a 400 over the wire",
      wrong.status_code == 400, wrong.text)

good = client.post(f"{base}/unlock", json={"unit_code": "ict800"})
check("the correct code unlocks (200)", good.status_code == 200, good.text)
check("the response says it is unlocked", good.json()["unlocked"] is True)

acting_as["user"] = lecturer
allowed = client.patch(f"{base}/{target.id}", json={"weight": 0.35})
check("the unlocked window permits ONE shape change",
      allowed.status_code == 200, allowed.text)
after = client.patch(f"{base}/{target.id}", json={"weight": 0.4})
check("the second change is refused - the window closed",
      after.status_code == 409, f"{after.status_code} {after.text}")

print("\n" + "=" * 60)
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections)")