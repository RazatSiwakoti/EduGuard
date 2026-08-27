"""Focused alert service checks using an in-memory SQLite database."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.models.base import Base
from app.models.email_message import EmailMessage
from app.models.email_template import EmailTemplate
from app.models.student import Student
from app.services import alert_service as service
from app.services.email_backend import SendOutcome
from app.services.email_render import render, unknown_placeholders


def make_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_templates_and_rendering():
    db = make_db()
    assert service.ensure_system_templates(db) == 3
    assert service.ensure_system_templates(db) == 0
    assert render("Hi {{ student_name }}", {"student_name": "Lin"}) == "Hi Lin"
    assert render("{{ attendance_pct }}", {}) == "not recorded"
    assert unknown_placeholders("{{ typo }}") == ["typo"]


def test_eligibility_and_suppression():
    db = make_db()
    student = Student(student_number="KOI-1", name="Lin", email="lin@example.com")
    db.add(student)
    db.flush()
    eligible, reason = service.check_eligibility(student, None, None, None, None, "automatic")
    assert not eligible and reason == "not_analysed"
    assert not service.is_suppressed(None, "high_risk")
    message = EmailMessage(kind="student_alert", student_id=student.id, unit_id=1, lecturer_id=1, recipient_email=student.email, subject="s", body="b", risk_tier="high_risk", queued_at=datetime.now(timezone.utc) - timedelta(days=1))
    assert service.is_suppressed(message, "high_risk")


def test_outbox_success_and_retry():
    db = make_db()
    message = EmailMessage(kind="student_alert", student_id=1, unit_id=1, lecturer_id=1, recipient_email="a@example.com", subject="s", body="b")
    db.add(message)
    db.commit()

    class Backend:
        def send(self, *args):
            return SendOutcome(True)

    assert service.drain_outbox(db, backend=Backend())["sent"] == 1
    assert db.get(EmailMessage, message.id).status == "sent"
