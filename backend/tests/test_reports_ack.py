"""
Acknowledgment in the report: aggregation, degradation, and what the
PDF actually says.

The point of this section is a distinction, not a number. Every figure
this system has ever reported about contacting a student describes what
the MAIL SERVER did. Acknowledgment is the first figure that comes from
the student. A report that prints both without saying which is which is
worse than one that prints only the first, so most of the checks below
are about wording rather than arithmetic - and the PDF ones read the
rendered page through `pdftotext`, not the object model, because text
hidden behind a layout bug should not count as text a reader saw.

Section [4] is the one worth reading: a deployment that has alerts but
cannot record receipts must report that fact about ITSELF, never a zero
that reads as a fact about the students.

Run:  cd backend && PYTHONPATH=. python3 tests/test_reports_ack.py
"""

import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import configure_mappers, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.models.criteria import Criteria
from app.models.email_message import EmailMessage
from app.models.enrollment import Enrollment
from app.models.enums import CriteriaCategory, UserRole
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.schemas.reports import ReportResponse
from app.services.report_pdf import build_report_pdf
from app.services.report_service import build_unit_report

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


def text_of(pdf: bytes) -> str:
    """The rendered text, as a reader would see it."""
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "r.pdf"
        source.write_bytes(pdf)
        result = subprocess.run(
            ["pdftotext", "-layout", str(source), "-"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=True,
        )
    return result.stdout


def flat(pdf_text: str) -> str:
    """
    Collapses every run of whitespace to one space.

    `pdftotext -layout` preserves the column layout, so a sentence that
    wrapped in the PDF comes back with a newline AND the indent of the
    next line inside it. Searching the raw output for a phrase that
    happens to wrap therefore fails on text a reader can plainly see -
    which is exactly what happened writing this suite.
    """
    return " ".join(pdf_text.split())


# ---------------------------------------------------------------------
# Fixture: one unit, four at-risk students, a realistic contact history
#
#   Priya   2 alerts sent, 1 confirmed
#   Dev     1 alert sent,  1 confirmed
#   Marta   1 alert sent,  never confirmed
#   Tom     1 alert FAILED (a bounce), so never confirmable
# ---------------------------------------------------------------------

def build_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    configure_mappers()
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


engine, db = build_db()

lecturer = User(email="bo@example.com", full_name="Bo Lecturer", role=UserRole.LECTURER, hashed_password="x", is_active=True)
db.add(lecturer)
db.commit()

unit = Unit(
    unit_code="ICT700", unit_name="Systems Analysis", year=2026,
    teaching_period="S2", level="master", start_date=date(2026, 2, 23),
    lecturer_id=lecturer.id, is_active=True, status="ASSIGNED",
)
db.add(unit)
db.commit()

for name, category, weight, max_score in (
    ("Quiz 1", CriteriaCategory.ASSESSMENT.value, 0.20, 20.0),
    ("Attendance", CriteriaCategory.ATTENDANCE.value, 0.50, 100.0),
):
    db.add(Criteria(
        unit_id=unit.id, name=name, category=category, weight=weight,
        max_score=max_score, threshold=50.0, enabled=True, sequence_number=1,
    ))
db.commit()

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


def make_student(number: str, name: str) -> Student:
    student = Student(student_number=number, name=name, email=f"{name.split()[0].lower()}@example.com")
    db.add(student)
    db.commit()
    db.add(Enrollment(student_id=student.id, unit_id=unit.id))
    scores = []
    for source in ("rule_based", "ml_model"):
        score = RiskScore(
            student_id=student.id, unit_id=unit.id, source=source,
            risk_score=0.7, risk_level="high_risk", is_incomplete=False, checkpoint_week=8,
        )
        db.add(score)
        scores.append(score)
    db.commit()
    db.add(FinalVerdict(
        student_id=student.id, unit_id=unit.id, checkpoint_week=8,
        rule_score_id=scores[0].id, ml_score_id=scores[1].id,
        final_tier="high_risk", requires_review=False,
    ))
    db.commit()
    return student


priya = make_student("KOI-2026-015", "Priya Sharma")
dev = make_student("KOI-2026-021", "Dev Alagappan")
marta = make_student("KOI-2026-033", "Marta Nowak")
tom = make_student("KOI-2026-044", "Tom Beattie")


def make_message(student, status, trigger, acknowledged_at=None, token=None):
    message = EmailMessage(
        kind="student_alert", student_id=student.id, unit_id=unit.id,
        lecturer_id=lecturer.id, recipient_email=student.email,
        recipient_name=student.name, subject="Checking in about ICT700",
        body="...", risk_tier="high_risk", trigger=trigger, status=status,
        queued_at=NOW - timedelta(days=2), ack_token=token,
        acknowledged_at=acknowledged_at,
    )
    db.add(message)
    db.commit()
    return message


make_message(priya, "sent", "automatic", acknowledged_at=NOW - timedelta(days=1), token="t1")
make_message(priya, "sent", "manual", token="t2")
make_message(dev, "sent", "automatic", acknowledged_at=NOW - timedelta(hours=3), token="t3")
make_message(marta, "sent", "automatic", token="t4")
make_message(tom, "failed", "automatic", token="t5")

# A lecturer summary, which is never acknowledgeable and must not be
# counted as an alert nobody confirmed.
db.add(EmailMessage(
    kind="lecturer_summary", unit_id=unit.id, lecturer_id=lecturer.id,
    recipient_email=lecturer.email, recipient_name=lecturer.full_name,
    subject="EduGuard: 4 alerts sent this week", body="...",
    trigger="automatic", status="sent", queued_at=NOW,
))
db.commit()

report = build_unit_report(db, lecturer.id, unit.id, checkpoint_week=8)
data = report["intervention"]


# ---------------------------------------------------------------------

heading("The aggregation counts receipts, not messages")

check("the alerts feature reports itself available", data["available"] is True)
check("acknowledgment reports itself available", data["acknowledgment_available"] is True)
check("five student alerts were counted", data["alerts_total"] == 5, str(data["alerts_total"]))
check("four were sent", data["alerts_sent"] == 4, str(data["alerts_sent"]))
check("one failed", data["alerts_failed"] == 1, str(data["alerts_failed"]))
check("TWO were confirmed received", data["alerts_acknowledged"] == 2, str(data["alerts_acknowledged"]))
check("by TWO distinct students", data["students_acknowledged"] == 2, str(data["students_acknowledged"]))
check("four distinct students were contacted", data["students_contacted"] == 4, str(data["students_contacted"]))
check("confirmations never exceed messages sent",
      data["alerts_acknowledged"] <= data["alerts_sent"])
check("students who confirmed never exceed students contacted",
      data["students_acknowledged"] <= data["students_contacted"])
check("the lecturer summary is not counted as an alert",
      data["alerts_total"] == 5, str(data["alerts_total"]))


heading("A student's own row carries both facts")

rows = {row["name"]: row for row in report["at_risk"]}
check("all four at-risk students are listed", len(rows) == 4, str(sorted(rows)))

check("Priya shows two alerts", rows["Priya Sharma"]["alerts_sent"] == 2)
check("...and ONE confirmation, not two", rows["Priya Sharma"]["alerts_acknowledged"] == 1,
      str(rows["Priya Sharma"]["alerts_acknowledged"]))
check("...with a timestamp for it", rows["Priya Sharma"]["last_acknowledged_at"] is not None)

check("Marta shows an alert", rows["Marta Nowak"]["alerts_sent"] == 1)
check("...and no confirmation", rows["Marta Nowak"]["alerts_acknowledged"] == 0)
check("...and no confirmation timestamp", rows["Marta Nowak"]["last_acknowledged_at"] is None)

check("Tom's failed alert still counts as an attempt", rows["Tom Beattie"]["alerts_sent"] == 1)
check("...and is not confirmable", rows["Tom Beattie"]["alerts_acknowledged"] == 0)

check("the response schema accepts the whole report", ReportResponse(**report) is not None)


heading("The PDF prints the distinction, not just the numbers")

body = text_of(build_report_pdf(report))

check("the intervention section still renders", "Intervention record" in body)
check("Confirmed received appears as a figure", "Confirmed received" in body, body[:0])
check("Students who confirmed appears", "Students who confirmed" in body)
check("both counts are printed", "2" in body)
check("the note explains where the number comes from",
      "from the student rather than from this system" in flat(body),
      flat(body)[:400])
check("it no longer ends at 'not a read receipt'",
      "is not a read receipt" not in flat(body),
      "the old apology is still in the document")
check("a confirmed student is flagged in the at-risk list",
      "confirmed received" in body.lower(), body[:0])
check("an unconfirmed student is NOT flagged with a zero",
      "0 confirmed received" not in body.lower())
check("the document still names every at-risk student",
      all(name in body for name in rows), str([n for n in rows if n not in body]))


heading("A deployment that cannot record receipts says so about ITSELF")

# The columns are dropped for real rather than mocked away: the guard is
# an `inspect()` call against the live database, and a monkeypatched
# flag would prove nothing about the branch that actually runs.
db.execute(text("ALTER TABLE email_messages DROP COLUMN acknowledged_at"))
db.commit()
db.expire_all()

legacy = build_unit_report(db, lecturer.id, unit.id, checkpoint_week=8)
legacy_data = legacy["intervention"]

check("alerts are still reported as available", legacy_data["available"] is True)
check("acknowledgment reports itself UNAVAILABLE", legacy_data["acknowledgment_available"] is False)
check("the alert counts are unaffected", legacy_data["alerts_sent"] == 4, str(legacy_data["alerts_sent"]))
check("confirmations read zero", legacy_data["alerts_acknowledged"] == 0)

caveats = " ".join(legacy["caveats"])
check("a caveat says receipts are NOT RECORDED here",
      "not recorded on this deployment" in caveats, caveats)
check("...and explicitly refuses the wrong reading",
      "not evidence that students did not receive" in caveats, caveats)

legacy_body = text_of(build_report_pdf(legacy))
check("the PDF drops the Confirmed figures entirely rather than printing zeros",
      "Confirmed received" not in legacy_body)
check("and states why in the note",
      "not recorded on this deployment" in flat(legacy_body), "")
check("the report still renders every other figure",
      "Intervention record" in legacy_body and "Alerts sent" in legacy_body)


heading("Sent but never confirmed is stated in words, not left to arithmetic")

engine2, db2 = build_db()
lect2 = User(email="l2@example.com", full_name="Di Lecturer", role=UserRole.LECTURER, hashed_password="x", is_active=True)
db2.add(lect2)
db2.commit()
unit2 = Unit(
    unit_code="ICT800", unit_name="Networks", year=2026, teaching_period="S2",
    level="master", start_date=date(2026, 2, 23), lecturer_id=lect2.id,
    is_active=True, status="ASSIGNED",
)
db2.add(unit2)
db2.commit()
db2.add(Criteria(
    unit_id=unit2.id, name="Quiz 1", category=CriteriaCategory.ASSESSMENT.value,
    weight=0.2, max_score=20.0, threshold=50.0, enabled=True, sequence_number=1,
))
db2.commit()

s2 = Student(student_number="KOI-2026-099", name="Ann Silent", email="ann@example.com")
db2.add(s2)
db2.commit()
db2.add(Enrollment(student_id=s2.id, unit_id=unit2.id))
pair = []
for source in ("rule_based", "ml_model"):
    score = RiskScore(student_id=s2.id, unit_id=unit2.id, source=source, risk_score=0.8,
                      risk_level="high_risk", is_incomplete=False, checkpoint_week=8)
    db2.add(score)
    pair.append(score)
db2.commit()
db2.add(FinalVerdict(student_id=s2.id, unit_id=unit2.id, checkpoint_week=8,
                     rule_score_id=pair[0].id, ml_score_id=pair[1].id,
                     final_tier="high_risk", requires_review=False))
db2.add(EmailMessage(
    kind="student_alert", student_id=s2.id, unit_id=unit2.id, lecturer_id=lect2.id,
    recipient_email=s2.email, recipient_name=s2.name, subject="Checking in",
    body="...", risk_tier="high_risk", trigger="automatic", status="sent",
    queued_at=NOW, ack_token="only",
))
db2.commit()

silent = build_unit_report(db2, lect2.id, unit2.id, checkpoint_week=8)
silent_caveats = " ".join(silent["caveats"])
check("a caveat says it was not confirmed",
      "not been confirmed as received" in silent_caveats, silent_caveats)
check("...and does not read 'None of the 1 alert'",
      "None of the 1" not in silent_caveats, silent_caveats)
check("...and says why that is not the same as ignored",
      "not a message a person has read" in silent_caveats, silent_caveats)
check("the caveat reaches the PDF",
      "not a message a person has read" in flat(text_of(build_report_pdf(silent))),
      flat(text_of(build_report_pdf(silent)))[:300])

# And the caveat must disappear once somebody confirms.
message = db2.query(EmailMessage).filter(EmailMessage.ack_token == "only").first()
message.acknowledged_at = NOW
db2.commit()
confirmed = build_unit_report(db2, lect2.id, unit2.id, checkpoint_week=8)
check("the caveat is gone once one student confirms",
      "not a message a person has read" not in " ".join(confirmed["caveats"]),
      " ".join(confirmed["caveats"]))
check("and the count moved to one", confirmed["intervention"]["alerts_acknowledged"] == 1)


heading("A unit nobody has been alerted about produces no acknowledgment noise")

db2.query(EmailMessage).delete()
db2.commit()
quiet = build_unit_report(db2, lect2.id, unit2.id, checkpoint_week=8)
quiet_caveats = " ".join(quiet["caveats"])
check("no confirmation caveat when nothing was sent",
      "not a message a person has read" not in quiet_caveats, quiet_caveats)
check("no not-recorded caveat either", "not recorded on this deployment" not in quiet_caveats, quiet_caveats)
check("the counts are all zero", quiet["intervention"]["alerts_acknowledged"] == 0)
check("the report still builds and renders",
      "Intervention record" in text_of(build_report_pdf(quiet)))


print("\n" + "=" * 62)
if failures:
    print(f"FAILED: {len(failures)} of {checks} checks across {section} sections")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"ALL CHECKS PASSED ({section} sections, {checks} checks)")