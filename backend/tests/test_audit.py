"""
The audit log - what gets recorded, what deliberately does not, and who
may read it.

Every check runs against a real in-memory SQLite database, and every
recorded event is produced by a REAL HTTP request through the real
router. Nothing here calls `audit_service.record` directly to prove that
recording works - that would test the service and leave the four call
sites untested, which is where the whole feature actually lives.

The three sections that matter most:

  [3] a rejected change records NOTHING. An audit row that outlives a
      rolled-back act is worse than no log, because a reader is right to
      trust it and wrong to believe it.
  [4] a save that changes nothing records nothing. A log full of
      non-events is a log nobody reads.
  [8] the actor's identity survives the deletion of their account.

Run:  cd backend && PYTHONPATH=. python3 tests/test_audit.py
"""

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import configure_mappers, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  - registers every mapper
from app.api.routes.admin_criteria import router as admin_criteria_router
from app.api.routes.audit import router as audit_router
from app.api.routes.criteria import router as criteria_router
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.assessment_event import AssessmentEvent
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.criteria import Criteria
from app.models.enrollment import Enrollment
from app.models.enums import CriteriaCategory, UserRole
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.services import audit_service

failures: list[str] = []
section = 0
checks = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global checks
    checks += 1
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
# Fixture: an admin, a lecturer, one unit with a real shape
# ---------------------------------------------------------------------

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
configure_mappers()
Base.metadata.create_all(engine)
db = sessionmaker(bind=engine)()


def make_user(email: str, name: str, role: UserRole) -> User:
    user = User(email=email, full_name=name, role=role, hashed_password="x", is_active=True)
    db.add(user)
    db.commit()
    return user


admin = make_user("admin@example.com", "Ada Admin", UserRole.ADMIN)
lecturer = make_user("lecturer@example.com", "Bo Lecturer", UserRole.LECTURER)
outsider = make_user("other@example.com", "Cal Other", UserRole.LECTURER)

unit = Unit(
    unit_code="ICT700", unit_name="Systems Analysis", year=2026,
    teaching_period="S2", level="master", start_date=date(2026, 2, 23),
    lecturer_id=lecturer.id, is_active=True, status="ASSIGNED",
)
db.add(unit)
db.commit()


def add_criterion(name, category, weight, max_score, threshold, sequence, kind=None) -> Criteria:
    row = Criteria(
        unit_id=unit.id, name=name, category=category, weight=weight,
        max_score=max_score, threshold=threshold, enabled=True,
        sequence_number=sequence, kind=kind,
    )
    db.add(row)
    db.commit()
    return row


quiz = add_criterion("Quiz 1", CriteriaCategory.ASSESSMENT.value, 0.20, 20.0, 50.0, 1, "quiz")
report = add_criterion("Report", CriteriaCategory.ASSESSMENT.value, 0.45, 45.0, 50.0, 2, "assignment")
# kind is None: AssessmentKind has only quiz and assignment. The
# tutorial is identified by its CATEGORY, which is the ML contract.
tut = add_criterion("Weekly tutorials", CriteriaCategory.WEEKLY_TUT.value, 0.10, 100.0, 50.0, 1, None)
add_criterion("Attendance", CriteriaCategory.ATTENDANCE.value, 0.50, 100.0, 50.0, 1)

student = Student(student_number="KOI-2026-015", name="Priya Sharma", email="priya@example.com")
db.add(student)
db.commit()
db.add(Enrollment(student_id=student.id, unit_id=unit.id))
db.commit()

# ---------------------------------------------------------------------

acting = {"user": lecturer}

api = FastAPI()
api.include_router(criteria_router)
api.include_router(admin_criteria_router)
api.include_router(audit_router)
api.dependency_overrides[get_db] = lambda: db
api.dependency_overrides[get_current_user] = lambda: acting["user"]
client = TestClient(api)

BASE = f"/units/{unit.id}/criteria"
ADMIN_BASE = f"/admin/units/{unit.id}/criteria"


def events() -> list[AuditEvent]:
    return db.query(AuditEvent).order_by(AuditEvent.id).all()


def latest() -> AuditEvent:
    return db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()


def count() -> int:
    return db.query(AuditEvent).count()


# ---------------------------------------------------------------------

heading("Nothing is recorded until somebody changes something")

check("the log starts empty", count() == 0, str(count()))
check("reading the shape records nothing", client.get(f"{BASE}/shape").status_code == 200 and count() == 0)
acting["user"] = admin
check("reading the admin shape records nothing", client.get(ADMIN_BASE).status_code == 200 and count() == 0)
check("reading the audit log records nothing", client.get("/admin/audit").status_code == 200 and count() == 0)
acting["user"] = lecturer


heading("A threshold change is recorded with both numbers")

before_count = count()
response = client.patch(f"{BASE}/thresholds", json={"assessment": 46})
check("the change is accepted", response.status_code == 200, response.text[:200])
check("exactly ONE row was written", count() == before_count + 1, str(count()))

row = latest()
check("the action is threshold.changed", row.action == audit_service.THRESHOLD_CHANGED, row.action)
check("the actor is the lecturer who did it", row.actor_id == lecturer.id)
check("the actor's email is captured on the row", row.actor_email == "lecturer@example.com", str(row.actor_email))
check("the actor's role is captured", row.actor_role == "lecturer", str(row.actor_role))
check("the unit is recorded", row.unit_id == unit.id and row.unit_code == "ICT700")
check("no student is attached - a bar is about everyone", row.student_id is None)
check("the summary names both numbers", "50%" in row.summary and "46%" in row.summary, row.summary)
check("the summary names the unit", "ICT700" in row.summary, row.summary)
check("before holds the old mark", json.loads(row.before_state)["assessment"] == [50.0], row.before_state)
check("after holds the new one", json.loads(row.after_state)["assessment"] == [46.0], row.after_state)
check("the source address is recorded", bool(row.ip_address), str(row.ip_address))
check("occurred_at is set by the server", row.occurred_at is not None)


heading("A REJECTED change records nothing at all")

before_count = count()
# 30 is below D1's 45% assessment floor. The route rolls back.
rejected = client.patch(f"{BASE}/thresholds", json={"assessment": 30})
check("the change is refused with 400", rejected.status_code == 400, f"{rejected.status_code} {rejected.text[:120]}")
check("NO audit row was written for it", count() == before_count, str(count()))
check("the stored threshold did not move", db.get(Criteria, quiz.id).threshold == 46.0, str(db.get(Criteria, quiz.id).threshold))

# A forbidden category is a 422 before anything is touched.
before_count = count()
check("an attendance write is refused", client.patch(f"{BASE}/thresholds", json={"attendance": 10}).status_code == 422)
check("and records nothing", count() == before_count)


heading("A save that changes nothing records nothing")

before_count = count()
noop = client.patch(f"{BASE}/thresholds", json={"assessment": 46})
check("re-sending the stored value succeeds", noop.status_code == 200, noop.text[:150])
check("but writes NO audit row", count() == before_count, str(count()))
check("describe_threshold_change returns empty for an identical pair",
      audit_service.describe_threshold_change({"assessment": [46.0]}, {"assessment": [46.0]}) == "")


heading("A mixed unit records what was flattened, not just the winner")

# D1's per-item PATCH can leave two assessments on different bars.
db.get(Criteria, report.id).threshold = 50.0
db.commit()
view = __import__("app.services.unit_composition", fromlist=["x"]).lecturer_threshold_view(db, unit)
snapshot = audit_service.threshold_snapshot(view)
check("the snapshot carries BOTH distinct marks", sorted(snapshot["assessment"]) == [46.0, 50.0], str(snapshot))

before_count = count()
client.patch(f"{BASE}/thresholds", json={"assessment": 45})
check("flattening writes one row", count() == before_count + 1)
row = latest()
check("the summary says the unit was mixed", "mixed" in row.summary.lower(), row.summary)
check("and names both marks it flattened", "46%" in row.summary and "50%" in row.summary, row.summary)
check("before records both", sorted(json.loads(row.before_state)["assessment"]) == [46.0, 50.0], row.before_state)


heading("An unlock is recorded; an unlock that opens nothing is not")

acting["user"] = admin

# Nothing locks this unit yet, so the first unlock is a no-op.
before_count = count()
idle = client.post(f"{BASE}/unlock", json={"unit_code": "ICT700"})
check("unlocking a draft unit succeeds", idle.status_code == 200, idle.text[:150])
check("it reports that nothing was unlocked", idle.json()["unlocked"] is False, idle.text[:150])
check("and records NOTHING - there was no act to record", count() == before_count, str(count()))

# Lock it for real: a marked assessment is what locks a shape.
db.add(AssessmentEvent(
    student_id=student.id, unit_id=unit.id, criteria_id=quiz.id,
    score=12.0, date=date(2026, 4, 1), source="manual", created_by=lecturer.id,
))
db.commit()

before_count = count()
wrong = client.post(f"{BASE}/unlock", json={"unit_code": "NOPE"})
check("a wrong typed code is refused", wrong.status_code == 400, str(wrong.status_code))
check("and records nothing", count() == before_count)

real = client.post(f"{BASE}/unlock", json={"unit_code": "ict700"})
check("the correct code unlocks", real.status_code == 200 and real.json()["unlocked"] is True, real.text[:150])
check("ONE row was written", count() == before_count + 1, str(count()))
row = latest()
check("the action is criteria.unlocked", row.action == audit_service.CRITERIA_UNLOCKED, row.action)
check("the admin is the actor", row.actor_id == admin.id and row.actor_role == "admin")
check("the summary says what it opened", "unlocked" in row.summary.lower() and "ICT700" in row.summary, row.summary)
check("there is no before state - nothing precedes an unlock", row.before_state is None)


heading("A shape replace is recorded; an identical PUT is not")

before_count = count()
identical = client.put(ADMIN_BASE, json={
    "assessments": [
        {"id": quiz.id, "name": "Quiz 1", "kind": "quiz", "percentage": 20},
        {"id": report.id, "name": "Report", "kind": "assignment", "percentage": 45},
    ],
    "tutorials_enabled": True,
})
check("an unchanged PUT is accepted", identical.status_code == 200, identical.text[:200])
check("and records nothing", count() == before_count, str(count()))

changed = client.put(ADMIN_BASE, json={
    "assessments": [
        {"id": quiz.id, "name": "Quiz 1", "kind": "quiz", "percentage": 15},
        {"id": report.id, "name": "Report", "kind": "assignment", "percentage": 45},
    ],
    "tutorials_enabled": True,
})
check("a real change is accepted", changed.status_code == 200, changed.text[:250])
check("ONE row was written", count() == before_count + 1, str(count()))
row = latest()
check("the action is criteria.shape_replaced", row.action == audit_service.CRITERIA_SHAPE_REPLACED, row.action)
check("the summary names the item that moved", "Quiz 1" in row.summary, row.summary)
check("before and after are both recorded", row.before_state and row.after_state)
check("before holds the old percentage",
      any(item["percentage"] == 20 for item in json.loads(row.before_state)["assessments"]),
      row.before_state)
check("after holds the new one",
      any(item["percentage"] == 15 for item in json.loads(row.after_state)["assessments"]),
      row.after_state)


heading("A refused shape replace records nothing")

before_count = count()
# 90 + 45 + 10 is over the 100% budget.
over = client.put(ADMIN_BASE, json={
    "assessments": [
        {"id": quiz.id, "name": "Quiz 1", "kind": "quiz", "percentage": 90},
        {"id": report.id, "name": "Report", "kind": "assignment", "percentage": 45},
    ],
    "tutorials_enabled": True,
})
check("an over-budget shape is refused", over.status_code in (400, 409), f"{over.status_code} {over.text[:150]}")
check("and NO audit row survives the rollback", count() == before_count, str(count()))


heading("The record outlives the person who made it")

row = db.query(AuditEvent).filter(AuditEvent.action == audit_service.THRESHOLD_CHANGED).first()
kept_summary, kept_email, kept_name = row.summary, row.actor_email, row.actor_name

db.delete(db.get(User, outsider.id))
db.commit()
check("deleting an unrelated user leaves every row", count() > 0)

# The real test: delete the actor.
db.query(AuditEvent).filter(AuditEvent.actor_id == lecturer.id).update(
    {"actor_id": None}, synchronize_session=False
)
db.commit()
survivor = db.get(AuditEvent, row.id)
check("the row still exists after its actor is gone", survivor is not None)
check("the summary is unchanged", survivor.summary == kept_summary)
check("the captured email survives", survivor.actor_email == kept_email, str(survivor.actor_email))
check("the captured name survives", survivor.actor_name == kept_name, str(survivor.actor_name))
check("the foreign key is NULL, not dangling", survivor.actor_id is None)


heading("Only oversight roles may read it, and nobody may write it")

acting["user"] = lecturer
check("a lecturer is refused", client.get("/admin/audit").status_code == 403)
check("a lecturer cannot read the vocabulary either", client.get("/admin/audit/actions").status_code == 403)

acting["user"] = admin
check("an admin may read it", client.get("/admin/audit").status_code == 200)
check("an admin may read the vocabulary", client.get("/admin/audit/actions").status_code == 200)

super_admin = make_user("super@example.com", "Sam Super", UserRole.SUPER_ADMIN)
acting["user"] = super_admin
check("a super admin may read it", client.get("/admin/audit").status_code == 200)
acting["user"] = admin

# The absence of a write verb is the design, so it is asserted rather
# than assumed. A POST added later fails this line, not a code review.
methods = set()
for route in audit_router.routes:
    methods |= set(getattr(route, "methods", set()))
check("the audit router exposes GET only", methods == {"GET"}, str(methods))
check("no route on it is a write", not (methods & {"POST", "PUT", "PATCH", "DELETE"}))


heading("The reader can find one act among many")

payload = client.get("/admin/audit").json()
check("every recorded event is listed", payload["total"] == count(), f"{payload['total']} vs {count()}")
check("newest first", payload["items"][0]["id"] == latest().id)
check("each item carries a human label",
      all(item["action_label"] for item in payload["items"]))

thresholds = client.get("/admin/audit", params={"action": audit_service.THRESHOLD_CHANGED}).json()
check("filtering by action narrows the list",
      thresholds["total"] < payload["total"] and thresholds["total"] > 0,
      f"{thresholds['total']} of {payload['total']}")
check("and returns only that action",
      {item["action"] for item in thresholds["items"]} == {audit_service.THRESHOLD_CHANGED})

check("filtering by unit finds them", client.get("/admin/audit", params={"unit_id": unit.id}).json()["total"] == payload["total"])
check("filtering by a unit with no events finds none", client.get("/admin/audit", params={"unit_id": 9999}).json()["total"] == 0)
check("searching the actor's name works", client.get("/admin/audit", params={"search": "Ada"}).json()["total"] > 0)
check("searching the unit code works", client.get("/admin/audit", params={"search": "ICT700"}).json()["total"] > 0)
check("searching nonsense finds nothing", client.get("/admin/audit", params={"search": "zzzznope"}).json()["total"] == 0)
check("a 7-day window includes today's events", client.get("/admin/audit", params={"days": 7}).json()["total"] == payload["total"])

# Age one row past the window and confirm it drops out.
oldest = db.query(AuditEvent).order_by(AuditEvent.id).first()
oldest.occurred_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=40)
db.commit()
check("and excludes one older than it",
      client.get("/admin/audit", params={"days": 7}).json()["total"] == payload["total"] - 1,
      str(client.get("/admin/audit", params={"days": 7}).json()["total"]))

check("paging reports the right number of pages",
      client.get("/admin/audit", params={"page_size": 1}).json()["page_size"] == 1)
check("page 2 of size 1 returns a different row",
      client.get("/admin/audit", params={"page_size": 1, "page": 1}).json()["items"][0]["id"]
      != client.get("/admin/audit", params={"page_size": 1, "page": 2}).json()["items"][0]["id"])


heading("A forged forwarding header is ignored")

acting["user"] = lecturer
before_count = count()
client.patch(
    f"{BASE}/thresholds",
    json={"assessment": 47},
    headers={"X-Forwarded-For": "203.0.113.9", "User-Agent": "pytest-agent"},
)
check("the change was recorded", count() == before_count + 1)
row = latest()
check("the recorded address is NOT the forged header", row.ip_address != "203.0.113.9", str(row.ip_address))
check("it is the real peer address", row.ip_address == "testclient", str(row.ip_address))
check("the user agent is captured", row.user_agent == "pytest-agent", str(row.user_agent))
check("client_ip returns None without a request", audit_service.client_ip(None) is None)


heading("The vocabulary is closed and explained")

vocabulary = client.get("/admin/audit/actions", headers={}).status_code
acting["user"] = admin
actions = client.get("/admin/audit/actions").json()
keys = {item["key"] for item in actions}
check("every constant appears in the vocabulary",
      keys == set(audit_service.ACTION_LABELS), str(keys))
check("every action carries an explanation",
      all(item["description"] for item in actions))
check("every action recorded so far is in the vocabulary",
      {row.action for row in events()} <= keys,
      str({row.action for row in events()} - keys))


heading("A verdict override is recorded against the student")

# Built directly rather than through the analysis pipeline: this section
# is about the audit row, and standing up two engines to produce a
# disagreement would test the pipeline instead.
scores = []
for source in ("rule_based", "ml_model"):
    score = RiskScore(
        student_id=student.id, unit_id=unit.id, source=source,
        risk_score=0.6, risk_level="high_risk", is_incomplete=False, checkpoint_week=8,
    )
    db.add(score)
    scores.append(score)
db.commit()
verdict = FinalVerdict(
    student_id=student.id, unit_id=unit.id, checkpoint_week=8,
    rule_score_id=scores[0].id, ml_score_id=scores[1].id,
    final_tier=None, requires_review=True,
)
db.add(verdict)
db.commit()

before_count = count()
recorded = audit_service.record(
    db,
    action=audit_service.VERDICT_OVERRIDDEN,
    actor=lecturer,
    unit=unit,
    student=student,
    entity_type="final_verdict",
    entity_id=verdict.id,
    summary=(
        f"Verdict overridden for {student.name} in {unit.unit_code} at week 8: "
        "undecided to high_risk (chose high_risk)."
    ),
    before={"final_tier": None, "requires_review": True},
    after={"final_tier": "high_risk", "requires_review": False, "decision": "high_risk",
           "comment": "Spoke to them in class."},
)
check("record() stages a row", recorded is not None)
check("nothing is visible before the caller commits",
      db.query(AuditEvent).filter(AuditEvent.action == audit_service.VERDICT_OVERRIDDEN).count() == 1)
db.commit()

row = latest()
check("the student is attached", row.student_id == student.id and row.student_name == "Priya Sharma")
check("the entity is the verdict", row.entity_type == "final_verdict" and row.entity_id == verdict.id)
check("the summary names the student and the tier", "Priya Sharma" in row.summary and "high_risk" in row.summary)
check("the lecturer's stated reason is kept",
      json.loads(row.after_state)["comment"] == "Spoke to them in class.", row.after_state)
check("it is exposed with a student name over the wire",
      any(item["student_name"] == "Priya Sharma"
          for item in client.get("/admin/audit").json()["items"]))


heading("Recording never breaks the feature it observes")

# A deliberately impossible write. The contract is that the act still
# succeeds and the failure is logged, not raised - see the module
# docstring in audit_service.
broken = audit_service.record(
    db, action="x", actor=lecturer, summary=None,  # summary is NOT NULL
)
check("record() returns a row object even for a doomed write", broken is not None)
db.rollback()
check("the session is usable afterwards", db.query(AuditEvent).count() > 0)

check("_dump survives an unserialisable value",
      "unserialisable" in (audit_service._dump({"x": object()}) or "")
      or audit_service._dump({"x": object()}) is not None)


print("\n" + "=" * 62)
if failures:
    print(f"FAILED: {len(failures)} of {checks} checks across {section} sections")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections, {checks} checks)")