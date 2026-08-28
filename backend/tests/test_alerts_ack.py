"""
Phase Email - acknowledgment portal, mail-backend switch, schedule config.

Every check below runs against a real in-memory SQLite database and, for
the portal, real HTTP requests through a real FastAPI app. Nothing here
asserts by reading the source.

The sections that matter most are [4] and [5]. [4] proves the GET does
not write, which is the difference between an acknowledgment that came
from a student and one that came from a mail scanner. [5] proves an
unknown token and a real one are indistinguishable to anyone who does
not already hold the real one.

Run:  cd backend && PYTHONPATH=. python3 tests/test_alerts_ack.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import configure_mappers, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  - registers every mapper
from app.api.routes.acknowledge import router as ack_router
from app.api.routes.alerts import router as lecturer_router
from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.base import Base
from app.models.criteria import Criteria
from app.models.email_message import EmailMessage
from app.models.email_template import EmailTemplate
from app.models.enrollment import Enrollment
from app.models.enums import UserRole
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.scheduler import DEFAULT_SWEEP_CRON, normalise_day_of_week
from app.services import alert_service as alerts
from app.services import email_backend
from app.services.email_render import ACK_MARKER, ensure_acknowledgement

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
# Fixture: one lecturer, one unit, three students, real verdicts
# ---------------------------------------------------------------------

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
configure_mappers()
Base.metadata.create_all(engine)
db = sessionmaker(bind=engine)()

lecturer = User(email="lecturer@example.com", full_name="Bo Lecturer", role=UserRole.LECTURER, hashed_password="x", is_active=True)
db.add(lecturer)
db.commit()

unit = Unit(unit_code="ICT700", unit_name="Systems Analysis", year=2026, teaching_period="S2", level="master", lecturer_id=lecturer.id, is_active=True, status="ASSIGNED")
db.add(unit)
db.commit()

db.add(Criteria(unit_id=unit.id, name="Quiz 1", category="assessment", weight=0.3, max_score=30.0, threshold=50.0, enabled=True, sequence_number=1))
db.commit()


def make_student(number: str, name: str, email: str | None, tier: str) -> Student:
    """A student with a full analysis behind them, so alerts are eligible."""
    student = Student(student_number=number, name=name, email=email)
    db.add(student)
    db.commit()
    db.add(Enrollment(student_id=student.id, unit_id=unit.id))
    scores = []
    for source in ("rule_based", "ml_model"):
        score = RiskScore(student_id=student.id, unit_id=unit.id, source=source, risk_score=0.7, risk_level=tier, is_incomplete=False, checkpoint_week=8)
        db.add(score)
        scores.append(score)
    db.commit()
    db.add(FinalVerdict(student_id=student.id, unit_id=unit.id, checkpoint_week=8, rule_score_id=scores[0].id, ml_score_id=scores[1].id, final_tier=tier, requires_review=False))
    db.commit()
    return student


amy = make_student("S0001", "Amy Nolan", "amy@example.com", "high_risk")
ben = make_student("S0002", "Ben Ortiz", "ben@example.com", "high_risk")
cal = make_student("S0003", "Cal Reyes", "cal@example.com", "high_risk")

alerts.ensure_system_templates(db)
template = db.query(EmailTemplate).filter(EmailTemplate.risk_tier == "high_risk").first()


def queue_for(student: Student) -> EmailMessage:
    row = next(item for item in alerts.evaluate_unit(db, unit, "manual") if item["student"].id == student.id)
    message = alerts.queue_alert(db, row["student"], unit, lecturer, row["verdict"], template, row["context"], "manual", lecturer.id)
    db.commit()
    return message


# ---------------------------------------------------------------------

heading("A queued student alert carries an unguessable token")

first = queue_for(amy)
second = queue_for(ben)
check("the message has a token", bool(first.ack_token), repr(first.ack_token))
check("the token is at least 32 characters", len(first.ack_token or "") >= 32, str(len(first.ack_token or "")))
check("two messages get different tokens", first.ack_token != second.ack_token)
check("the token is URL-safe", all(c.isalnum() or c in "-_" for c in first.ack_token or ""))
check("it starts unacknowledged", first.acknowledged_at is None)
check("the link is absolute and points at PUBLIC_BASE_URL", alerts.acknowledge_url("abc").startswith(settings.PUBLIC_BASE_URL.rstrip("/")))


heading("The acknowledgment link reaches the student, whatever the template says")

check("the rendered body contains the link", ACK_MARKER in first.body and (first.ack_token or "") in first.body)
check("the stored body is what was rendered, link included", first.body.count(ACK_MARKER) == 1)

# A lecturer who places the placeholder themselves must not get two.
custom = EmailTemplate(lecturer_id=lecturer.id, name="Mine", risk_tier="high_risk", subject="About {{unit_code}}", body="Hi {{student_name}} - confirm here: {{acknowledge_url}} - thanks.", is_system=False)
db.add(custom)
db.commit()
row = next(item for item in alerts.evaluate_unit(db, unit, "manual") if item["student"].id == cal.id)
placed = alerts.queue_alert(db, row["student"], unit, lecturer, row["verdict"], custom, row["context"], "manual", lecturer.id)
db.commit()
check("a template using the placeholder gets exactly ONE link", placed.body.count(ACK_MARKER) == 1, placed.body)
check("the link sits where the lecturer put it, not appended", placed.body.rstrip().endswith("- thanks."), placed.body)
check("ensure_acknowledgement is idempotent", ensure_acknowledgement(placed.body, "http://x/alerts/acknowledge/z") == placed.body)


heading("A lecturer summary is never acknowledgeable")

summary = alerts.queue_lecturer_summary(db, lecturer, [first], {})
db.commit()
check("the summary has no token", summary.ack_token is None)
check("two summaries can coexist with NULL tokens", alerts.queue_lecturer_summary(db, lecturer, [second], {}) is not None)
db.commit()
check("the unique index tolerates many NULLs", db.query(EmailMessage).filter(EmailMessage.ack_token.is_(None)).count() >= 2)


heading("acknowledge() records once, and only once")

before = alerts.acknowledge(db, first.ack_token)
check("a valid token resolves to the message", before is not None and before.id == first.id)
check("the timestamp is now set", before.acknowledged_at is not None)
stamped = before.acknowledged_at
again = alerts.acknowledge(db, first.ack_token)
check("a second call still returns the message", again is not None and again.id == first.id)
check("the timestamp did NOT move", again.acknowledged_at == stamped, f"{again.acknowledged_at} != {stamped}")
check("an unknown token returns None", alerts.acknowledge(db, "not-a-real-token") is None)
check("an empty token returns None", alerts.acknowledge(db, "") is None)
check("whitespace is not a token", alerts.acknowledge(db, "   ") is None)


heading("Over real HTTP: the GET does not write, the POST does")

api = FastAPI()
api.include_router(ack_router)
api.include_router(lecturer_router)
api.dependency_overrides[get_db] = lambda: db
api.dependency_overrides[get_current_user] = lambda: lecturer
client = TestClient(api)

fresh = queue_for(make_student("S0004", "Dee Walsh", "dee@example.com", "high_risk"))
url = f"/alerts/acknowledge/{fresh.ack_token}"

get_one = client.get(url)
check("GET returns 200", get_one.status_code == 200, get_one.text[:200])
db.refresh(fresh)
check("GET DID NOT acknowledge - a link scanner cannot sign for a student", fresh.acknowledged_at is None, str(fresh.acknowledged_at))
check("GET offers a form to submit", "<form" in get_one.text and 'method="post"' in get_one.text)
check("GET does NOT print the risk tier", "high_risk" not in get_one.text.lower() and "High Risk" not in get_one.text)
check("GET does NOT print the message body", "Tutorial submissions" not in get_one.text)
check("GET does name the student, so they know it is theirs", "Dee Walsh" in get_one.text)
check("GET names the unit", "ICT700" in get_one.text)

post = client.post(url)
check("POST returns 200", post.status_code == 200, post.text[:200])
db.refresh(fresh)
check("POST DID acknowledge", fresh.acknowledged_at is not None)
check("the receipt states a time", "Recorded on" in post.text)
check("the time is in the institution's timezone, not UTC", "AEST" in post.text or "AEDT" in post.text, post.text[post.text.find("Recorded on"):][:80])
check("the hour is not zero-padded", " 0" not in post.text[post.text.find("Recorded on"):][:60].split(" at ")[-1])

repeat_get = client.get(url)
recorded = fresh.acknowledged_at
db.refresh(fresh)
check("a later GET shows the receipt, not the button", "<form" not in repeat_get.text)
check("and still did not move the timestamp", fresh.acknowledged_at == recorded)


heading("An unknown token is indistinguishable from a real one")

missing_get = client.get("/alerts/acknowledge/" + "z" * 43)
missing_post = client.post("/alerts/acknowledge/" + "z" * 43)
check("GET on a guessed token is 404", missing_get.status_code == 404)
check("POST on a guessed token is 404", missing_post.status_code == 404)
check("both render the same page - no oracle", missing_get.text == missing_post.text)
check("the 404 leaks no student name", "Dee Walsh" not in missing_get.text and "Amy Nolan" not in missing_get.text)

summary_token_probe = client.get(f"/alerts/acknowledge/{'y' * 40}")
check("a nonexistent token cannot be told from a summary's", summary_token_probe.status_code == 404)


heading("The receipt page cannot leak the token sideways")

check("Referrer-Policy is no-referrer", get_one.headers.get("referrer-policy") == "no-referrer")
check("X-Robots-Tag blocks indexing", "noindex" in (get_one.headers.get("x-robots-tag") or ""))
check("Cache-Control is no-store", get_one.headers.get("cache-control") == "no-store")
check("the receipt links NOWHERE - a student has no account to be sent to", "<a " not in post.text)
check("the confirm page links nowhere either", "<a " not in get_one.text)
check("the 404 page carries the same headers", missing_get.headers.get("referrer-policy") == "no-referrer")


heading("The portal needs no authentication, and the lecturer API still does")

check("no auth dependency is declared on the public router", ack_router.dependencies == [])
check("the lecturer router still declares one", len(lecturer_router.dependencies) == 1)


heading("The lecturer sees acknowledgment in the log and the tiles")

log = client.get("/lecturer/alerts/log").json()
rows = {item["id"]: item for item in log["items"]}
check("the log exposes acknowledged_at", "acknowledged_at" in next(iter(rows.values())))
check("the acknowledged message reports a timestamp", rows[fresh.id]["acknowledged_at"] is not None)
check("an unacknowledged one reports null", rows[second.id]["acknowledged_at"] is None)

# Only SENT student alerts count toward the denominator.
for message in db.query(EmailMessage).all():
    message.status = "sent" if message.id in (first.id, fresh.id, second.id) else "queued"
db.commit()
counters = client.get("/lecturer/alerts/summary").json()["counters"]
check("acknowledged counts only confirmed receipts", counters["acknowledged"] == 2, str(counters))
check("the denominator is sent STUDENT alerts only", counters["acknowledgeable"] == 3, str(counters))
check("the denominator never exceeds sent", counters["acknowledgeable"] <= counters["sent"], str(counters))
check("acknowledged never exceeds the denominator", counters["acknowledged"] <= counters["acknowledgeable"])


heading("The preview shows the lecturer what the student will actually get")

preview = client.post("/lecturer/alerts/preview", json={"student_id": amy.id, "unit_id": unit.id, "template_id": template.id}).json()
check("the preview includes the acknowledgment footer", ACK_MARKER in preview["body"])
check("the preview link is inert", "preview-link-not-active" in preview["body"])
check("previewing stored nothing", db.query(EmailMessage).filter(EmailMessage.ack_token == "preview-link-not-active").count() == 0)
check("the preview body has no real token in it", not any((message.ack_token or "@@") in preview["body"] for message in db.query(EmailMessage).all()))


heading("EMAIL_BACKEND decides, then ENVIRONMENT, then console")

cases = [
    ("smtp", "development", email_backend.SmtpBackend, "explicit smtp wins over a dev environment"),
    ("console", "production", email_backend.ConsoleBackend, "explicit console wins over production"),
    ("", "production", email_backend.SmtpBackend, "an unset key falls back to the old ENVIRONMENT rule"),
    ("", "development", email_backend.ConsoleBackend, "unset plus development stays safe"),
    ("SMTP", "development", email_backend.SmtpBackend, "the value is case-insensitive"),
    ("banana", "development", email_backend.ConsoleBackend, "an unrecognised value resolves to the SAFE side"),
    ("banana", "production", email_backend.SmtpBackend, "and still honours an explicit production"),
]
original_backend, original_env = settings.EMAIL_BACKEND, settings.ENVIRONMENT
for value, environment, expected, label in cases:
    settings.EMAIL_BACKEND, settings.ENVIRONMENT = value, environment
    check(label, isinstance(email_backend.get_email_backend(), expected))
settings.EMAIL_BACKEND, settings.ENVIRONMENT = original_backend, original_env


heading("ALERT_SWEEP_CRON: the day-of-week trap is closed")

from apscheduler.triggers.cron import CronTrigger  # noqa: E402  - local to this section

FRIDAY = datetime(2026, 8, 28, 12, 0, tzinfo=timezone(timedelta(hours=10)))


def next_day(expression: str) -> str:
    trigger = CronTrigger.from_crontab(normalise_day_of_week(expression))
    return trigger.get_next_fire_time(None, FRIDAY).strftime("%A")


check("APScheduler really does read '1' as Tuesday - the bug is real", CronTrigger.from_crontab("0 8 * * 1").get_next_fire_time(None, FRIDAY).strftime("%A") == "Tuesday")
check("'0 8 * * 1' is translated to Monday", next_day("0 8 * * 1") == "Monday", next_day("0 8 * * 1"))
check("'0 8 * * 0' is translated to Sunday", next_day("0 8 * * 0") == "Sunday", next_day("0 8 * * 0"))
check("'0 8 * * 7' is also Sunday", next_day("0 8 * * 7") == "Sunday")
check("a day NAME is left alone", normalise_day_of_week("0 8 * * mon") == "0 8 * * mon")
check("a range is translated whole", normalise_day_of_week("0 8 * * 1-5") == "0 8 * * mon-fri")
check("a list is translated", normalise_day_of_week("0 8 * * 1,4") == "0 8 * * mon,thu")
check("a step is NOT rewritten - the digit is a step, not a day", normalise_day_of_week("0 8 * * */2") == "0 8 * * */2")
check("'*' is untouched", normalise_day_of_week("*/5 * * * *") == "*/5 * * * *")
check("a demo cron fires within five minutes", next_day("*/5 * * * *") == "Friday")
check("the default is written as a name", "mon" in DEFAULT_SWEEP_CRON)
check("a malformed expression is passed through unchanged for the caller to reject", normalise_day_of_week("nonsense") == "nonsense")


heading("CHECKPOINT_WEEK is finally read from config")

check("alert_service takes its checkpoint from settings", alerts.DEFAULT_CHECKPOINT_WEEK == settings.CHECKPOINT_WEEK, f"{alerts.DEFAULT_CHECKPOINT_WEEK} vs {settings.CHECKPOINT_WEEK}")
check("and the API reports the same number", client.get("/lecturer/alerts/summary").json()["checkpoint_week"] == settings.CHECKPOINT_WEEK)


print("\n" + "=" * 62)
if failures:
    print(f"FAILED: {len(failures)} of {checks} checks across {section} sections")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections, {checks} checks)")
