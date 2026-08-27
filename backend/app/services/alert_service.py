"""Alert eligibility, queueing, dispatch, and weekly sweep services."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.assessment_event import AssessmentEvent
from app.models.criteria import Criteria
from app.models.email_message import EmailMessage
from app.models.email_template import EmailTemplate
from app.models.enrollment import Enrollment
from app.models.final_verdicts import FinalVerdict
from app.models.risk_score import RiskScore
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.services.email_backend import get_email_backend
from app.services.email_render import SYSTEM_TEMPLATES, render

DEFAULT_CHECKPOINT_WEEK = 8
AUTO_ALERT_TIERS = ("high_risk",)
SUPPRESSION_DAYS = 7
MAX_ATTEMPTS = 3
_TIER_SEVERITY = {"high_risk": 3, "low_risk": 2, "safe": 1}
TIER_LABELS = {"high_risk": "High Risk", "low_risk": "Low Risk", "safe": "Safe"}
BLOCKED_REASONS = {
    "no_email": "No email address on record for this student",
    "not_analysed": "The analysis has never been run for this student",
    "needs_review": "The engines disagreed - resolve the review first",
    "incomplete_data": "Scored on incomplete data - not safe to send automatically",
    "recently_alerted": f"Already alerted in the last {SUPPRESSION_DAYS} days",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class advisory_lock:
    def __init__(self, db: Session, key: int):
        self.db, self.key, self.acquired = db, key, False

    def __enter__(self):
        if self.db.bind is None or self.db.bind.dialect.name != "postgresql":
            self.acquired = True
        else:
            self.acquired = bool(self.db.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": self.key}).scalar())
        return self

    def __exit__(self, *exc):
        if self.acquired and self.db.bind is not None and self.db.bind.dialect.name == "postgresql":
            self.db.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": self.key})
        return False


SWEEP_LOCK_KEY = 780_001
DRAIN_LOCK_KEY = 780_002


def ensure_system_templates(db: Session) -> int:
    existing = {row.risk_tier for row in db.execute(select(EmailTemplate).where(EmailTemplate.is_system.is_(True))).scalars()}
    created = 0
    for template in SYSTEM_TEMPLATES:
        if template["risk_tier"] not in existing:
            db.add(EmailTemplate(lecturer_id=None, name=template["name"], risk_tier=template["risk_tier"], subject=template["subject"], body=template["body"], is_system=True))
            created += 1
    if created:
        db.commit()
    return created


def resolve_template(db: Session, lecturer_id: int, tier: str, template_id: Optional[int] = None) -> Optional[EmailTemplate]:
    if template_id is not None:
        chosen = db.get(EmailTemplate, template_id)
        if chosen and (chosen.is_system or chosen.lecturer_id == lecturer_id):
            return chosen
    own = db.execute(select(EmailTemplate).where(EmailTemplate.lecturer_id == lecturer_id, EmailTemplate.risk_tier == tier).order_by(EmailTemplate.updated_at.desc(), EmailTemplate.id.desc()).limit(1)).scalars().first()
    if own:
        return own
    return db.execute(select(EmailTemplate).where(EmailTemplate.is_system.is_(True), EmailTemplate.risk_tier == tier)).scalars().first()


def _latest_events(db: Session, unit_id: int) -> dict[tuple[int, int], AssessmentEvent]:
    latest = {}
    for event in db.execute(select(AssessmentEvent).where(AssessmentEvent.unit_id == unit_id).order_by(AssessmentEvent.date.desc(), AssessmentEvent.id.desc())).scalars().all():
        latest.setdefault((event.student_id, event.criteria_id), event)
    return latest


def build_context(student, unit, lecturer, tier, criteria, events, checkpoint_week):
    context = {"student_name": student.name, "student_number": student.student_number, "unit_code": unit.unit_code, "unit_name": unit.unit_name, "lecturer_name": (lecturer.full_name if lecturer else None) or "your lecturer", "risk_level": TIER_LABELS.get(tier or "", "Unknown"), "checkpoint_week": checkpoint_week}
    assessment_total = assessment_marked = 0
    for criterion in criteria:
        event = events.get((student.id, criterion.id))
        if criterion.category is None:
            continue
        category = criterion.category.value
        if category == "attendance" and event is not None:
            context.setdefault("attendance_pct", f"{round(event.score)}%")
        elif category == "weekly_tut" and event is not None:
            context.setdefault("tutorial_pct", f"{round(event.score)}%")
        elif category == "assessment":
            assessment_total += 1
            assessment_marked += event is not None
    if assessment_total:
        context["assessments_marked"] = f"{assessment_marked} of {assessment_total}"
    return context


def last_alert_for(db: Session, student_id: int, unit_id: int) -> Optional[EmailMessage]:
    return db.execute(select(EmailMessage).where(EmailMessage.kind == "student_alert", EmailMessage.student_id == student_id, EmailMessage.unit_id == unit_id).order_by(EmailMessage.queued_at.desc(), EmailMessage.id.desc()).limit(1)).scalars().first()


def is_suppressed(last, tier: str, now: Optional[datetime] = None) -> bool:
    if last is None or _as_aware(last.queued_at) is None:
        return False
    if (now or _now()) - _as_aware(last.queued_at) >= timedelta(days=SUPPRESSION_DAYS):
        return False
    return _TIER_SEVERITY.get(tier, 0) <= _TIER_SEVERITY.get(last.risk_tier or "", 0)


def check_eligibility(student, verdict, rule_score, ml_score, last, trigger, now=None):
    if not (student.email or "").strip():
        return False, "no_email"
    if verdict is None:
        return False, "not_analysed"
    if verdict.requires_review or verdict.final_tier is None:
        return False, "needs_review"
    if (rule_score and rule_score.is_incomplete) or (ml_score and ml_score.is_incomplete):
        return False, "incomplete_data"
    if trigger == "automatic":
        if verdict.final_tier not in AUTO_ALERT_TIERS:
            return False, None
        if is_suppressed(last, verdict.final_tier, now):
            return False, "recently_alerted"
    return True, None


def queue_alert(db, student, unit, lecturer, verdict, template, context, trigger, created_by=None):
    message = EmailMessage(kind="student_alert", student_id=student.id, unit_id=unit.id, lecturer_id=unit.lecturer_id, recipient_email=(student.email or "").strip(), recipient_name=student.name, subject=render(template.subject, context), body=render(template.body, context), template_id=template.id, template_name=template.name, risk_tier=verdict.final_tier, verdict_id=verdict.id, trigger=trigger, status="queued", created_by=created_by)
    db.add(message)
    return message


def queue_lecturer_summary(db, lecturer, queued, failed_reasons):
    if not queued:
        return None
    lines = [f"Hi {lecturer.full_name or 'there'},", "", f"EduGuard sent {len(queued)} automatic alert{'s' if len(queued) != 1 else ''} on your behalf this week:", ""]
    for message in queued:
        lines.append(f"  - {message.recipient_name} ({message.recipient_email}) - {message.unit.unit_code if message.unit else 'unit'} - {TIER_LABELS.get(message.risk_tier or '', message.risk_tier or '')}")
    if failed_reasons:
        lines += ["", "Students who could NOT be alerted automatically:", ""]
        lines.extend(f"  - {count} x {BLOCKED_REASONS.get(reason, reason)}" for reason, count in sorted(failed_reasons.items()))
    lines += ["", "These have already been sent. You can see every message, and contact anyone the sweep skipped, on the Alerts page.", "", "EduGuard"]
    message = EmailMessage(kind="lecturer_summary", lecturer_id=lecturer.id, recipient_email=(lecturer.email or "").strip(), recipient_name=lecturer.full_name, subject=f"EduGuard: {len(queued)} alert{'s' if len(queued) != 1 else ''} sent this week", body="\n".join(lines), trigger="automatic", status="queued")
    db.add(message)
    return message


def drain_outbox(db: Session, limit: int = 50, backend=None):
    backend = backend or get_email_backend()
    counts = {"sent": 0, "failed": 0, "retrying": 0}
    with advisory_lock(db, DRAIN_LOCK_KEY) as lock:
        if not lock.acquired:
            return counts
        pending = db.execute(select(EmailMessage).where(EmailMessage.status == "queued", EmailMessage.attempts < MAX_ATTEMPTS).order_by(EmailMessage.queued_at, EmailMessage.id).limit(limit)).scalars().all()
        for message in pending:
            message.attempts += 1
            outcome = backend.send(message.recipient_email, message.recipient_name, message.subject, message.body)
            if outcome.ok:
                message.status, message.sent_at, message.error = "sent", _now(), None
                counts["sent"] += 1
            elif outcome.retryable and message.attempts < MAX_ATTEMPTS:
                message.error = outcome.error
                counts["retrying"] += 1
            else:
                message.status, message.error = "failed", outcome.error
                counts["failed"] += 1
            db.commit()
    return counts


def _latest_verdicts(db, unit_id, checkpoint_week):
    latest = {}
    for verdict in db.execute(select(FinalVerdict).where(FinalVerdict.unit_id == unit_id, FinalVerdict.checkpoint_week == checkpoint_week).order_by(FinalVerdict.created_at.desc(), FinalVerdict.id.desc())).scalars().all():
        latest.setdefault(verdict.student_id, verdict)
    return latest


def evaluate_unit(db, unit, trigger, checkpoint_week=DEFAULT_CHECKPOINT_WEEK, now=None):
    lecturer = db.get(User, unit.lecturer_id) if unit.lecturer_id else None
    criteria = db.execute(select(Criteria).where(Criteria.unit_id == unit.id, Criteria.enabled.is_(True)).order_by(Criteria.id)).scalars().all()
    events, verdicts = _latest_events(db, unit.id), _latest_verdicts(db, unit.id, checkpoint_week)
    students = db.execute(select(Student).join(Enrollment, Enrollment.student_id == Student.id).where(Enrollment.unit_id == unit.id).order_by(Student.name)).scalars().all()
    score_ids = [score_id for verdict in verdicts.values() for score_id in (verdict.rule_score_id, verdict.ml_score_id)]
    scores = {score.id: score for score in db.execute(select(RiskScore).where(RiskScore.id.in_(score_ids))).scalars()} if score_ids else {}
    rows = []
    for student in students:
        verdict = verdicts.get(student.id)
        rule_score = scores.get(verdict.rule_score_id) if verdict else None
        ml_score = scores.get(verdict.ml_score_id) if verdict else None
        last = last_alert_for(db, student.id, unit.id)
        eligible, reason = check_eligibility(student, verdict, rule_score, ml_score, last, trigger, now)
        rows.append({"student": student, "unit": unit, "lecturer": lecturer, "verdict": verdict, "eligible": eligible, "blocked_reason": reason, "last_alert": last, "context": build_context(student, unit, lecturer, verdict.final_tier if verdict else None, list(criteria), events, checkpoint_week)})
    return rows


def sweep_units(db, units, checkpoint_week=DEFAULT_CHECKPOINT_WEEK, now=None):
    summary = {"units": 0, "queued": 0, "skipped": {}, "locked_out": False}
    with advisory_lock(db, SWEEP_LOCK_KEY) as lock:
        if not lock.acquired:
            summary["locked_out"] = True
            return summary
        by_lecturer, blocked_by_lecturer = {}, {}
        for unit in units:
            summary["units"] += 1
            for row in evaluate_unit(db, unit, "automatic", checkpoint_week, now):
                if not row["eligible"]:
                    reason = row["blocked_reason"]
                    if reason:
                        summary["skipped"][reason] = summary["skipped"].get(reason, 0) + 1
                        blocked = blocked_by_lecturer.setdefault(unit.lecturer_id, {})
                        blocked[reason] = blocked.get(reason, 0) + 1
                    continue
                verdict = row["verdict"]
                template = resolve_template(db, unit.lecturer_id, verdict.final_tier)
                if template is None:
                    summary["skipped"]["no_template"] = summary["skipped"].get("no_template", 0) + 1
                    continue
                message = queue_alert(db, row["student"], unit, row["lecturer"], verdict, template, row["context"], "automatic")
                by_lecturer.setdefault(unit.lecturer_id, []).append(message)
                summary["queued"] += 1
        db.flush()
        for lecturer_id, messages in by_lecturer.items():
            lecturer = db.get(User, lecturer_id)
            if lecturer and (lecturer.email or "").strip():
                queue_lecturer_summary(db, lecturer, messages, blocked_by_lecturer.get(lecturer_id, {}))
        db.commit()
    return summary


def active_units(db, lecturer_id=None):
    stmt = select(Unit).where(Unit.is_active.is_(True), Unit.lecturer_id.is_not(None))
    if lecturer_id is not None:
        stmt = stmt.where(Unit.lecturer_id == lecturer_id)
    return list(db.execute(stmt).scalars())


def sweep_all_units(db, checkpoint_week=DEFAULT_CHECKPOINT_WEEK, now=None):
    return sweep_units(db, active_units(db), checkpoint_week, now)
