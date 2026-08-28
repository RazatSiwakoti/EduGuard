"""Lecturer alerts API (Phase 7.8), scoped to the authenticated lecturer."""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_teaching_role
from app.database import SessionLocal, get_db
from app.models.email_message import EmailMessage
from app.models.email_template import EmailTemplate
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.schemas.alerts import (
    AlertCounters, AlertLogItem, AlertLogPage, AlertQueue, AlertSummary,
    BulkSendRequest, PlaceholderOut, PreviewOut, QueueItem, SendRequest,
    SendResult, TemplateOut, TemplateSave,
)
from app.services import alert_service as alerts
from app.services.email_backend import ConsoleBackend, get_email_backend
from app.services.email_render import (
    PLACEHOLDERS,
    ensure_acknowledgement,
    render,
    unknown_placeholders,
)

router = APIRouter(prefix="/lecturer/alerts", tags=["Lecturer - Alerts"], dependencies=[Depends(require_teaching_role())])


def _my_units(db, lecturer_id):
    return list(db.execute(select(Unit).where(Unit.lecturer_id == lecturer_id, Unit.is_active.is_(True)).order_by(Unit.unit_code)).scalars())


def _owned_unit(db, unit_id, lecturer_id):
    return db.execute(select(Unit).where(Unit.id == unit_id, Unit.lecturer_id == lecturer_id)).scalars().first()


def _drain_in_background():
    db = SessionLocal()
    try:
        alerts.drain_outbox(db)
    finally:
        db.close()


def _queue_item(row):
    student, unit, verdict, last = row["student"], row["unit"], row["verdict"], row["last_alert"]
    reason = row["blocked_reason"]
    return QueueItem(student_id=student.id, student_number=student.student_number, name=student.name, email=student.email, unit_id=unit.id, unit_code=unit.unit_code, risk_tier=verdict.final_tier if verdict else None, eligible=row["eligible"], blocked_reason=reason, blocked_detail=alerts.BLOCKED_REASONS.get(reason) if reason else None, last_alert_at=last.queued_at if last else None, last_alert_status=last.status if last else None)


@router.get("/summary", response_model=AlertSummary)
def read_summary(db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    rows = db.execute(select(EmailMessage.status, EmailMessage.kind, EmailMessage.acknowledged_at).where(EmailMessage.lecturer_id == current_user.id)).all()
    statuses = [row[0] for row in rows]
    # The denominator for acknowledgment is student alerts that actually
    # went out. A queued message has not been offered to anyone yet, and
    # a failed one never arrived - counting either would make the ratio
    # report a student's silence as a fact about the student.
    acknowledgeable = [row for row in rows if row[1] == "student_alert" and row[0] == "sent"]
    backend = get_email_backend()
    console = isinstance(backend, ConsoleBackend)
    return AlertSummary(counters=AlertCounters(total=len(statuses), sent=statuses.count("sent"), failed=statuses.count("failed"), queued=statuses.count("queued"), acknowledged=sum(1 for row in acknowledgeable if row[2] is not None), acknowledgeable=len(acknowledgeable)), unit_count=len(_my_units(db, current_user.id)), checkpoint_week=alerts.DEFAULT_CHECKPOINT_WEEK, dry_run=console, outbox_path=str(backend.outbox) if console else None)


@router.get("/queue", response_model=AlertQueue)
def read_queue(unit_id: Optional[int] = Query(default=None, ge=1), db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    units = _my_units(db, current_user.id)
    if unit_id is not None:
        units = [unit for unit in units if unit.id == unit_id]
        if not units:
            raise HTTPException(status_code=404, detail="No such unit you teach.")
    ready, blocked = [], []
    for unit in units:
        for row in alerts.evaluate_unit(db, unit, "manual"):
            item = _queue_item(row)
            if item.eligible:
                ready.append(item)
            elif item.blocked_reason:
                blocked.append(item)
    severity = {"high_risk": 0, "low_risk": 1, "safe": 2}
    ready.sort(key=lambda item: (severity.get(item.risk_tier or "", 3), item.name))
    blocked.sort(key=lambda item: (item.blocked_reason or "", item.name))
    return AlertQueue(ready=ready, blocked=blocked)


@router.get("/log", response_model=AlertLogPage)
def read_log(status: Optional[str] = Query(default=None), search: Optional[str] = Query(default=None), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    stmt = select(EmailMessage).where(EmailMessage.lecturer_id == current_user.id)
    if status in ("sent", "failed", "queued"):
        stmt = stmt.where(EmailMessage.status == status)
    needle = (search or "").strip().lower()
    if needle:
        pattern = f"%{needle}%"
        stmt = stmt.outerjoin(Student, Student.id == EmailMessage.student_id).where(EmailMessage.recipient_email.ilike(pattern) | EmailMessage.subject.ilike(pattern) | Student.name.ilike(pattern) | Student.student_number.ilike(pattern))
    rows = db.execute(stmt.order_by(EmailMessage.queued_at.desc(), EmailMessage.id.desc())).scalars().all()
    items = []
    for message in rows[(page - 1) * page_size:page * page_size]:
        student = db.get(Student, message.student_id) if message.student_id else None
        unit = db.get(Unit, message.unit_id) if message.unit_id else None
        items.append(AlertLogItem(id=message.id, kind=message.kind, student_id=message.student_id, student_name=student.name if student else None, student_number=student.student_number if student else None, unit_code=unit.unit_code if unit else None, recipient_email=message.recipient_email, subject=message.subject, body=message.body, template_name=message.template_name, risk_tier=message.risk_tier, trigger=message.trigger, status=message.status, error=message.error, attempts=message.attempts, queued_at=message.queued_at, sent_at=message.sent_at, acknowledged_at=message.acknowledged_at))
    return AlertLogPage(items=items, total=len(rows), page=page, page_size=page_size)


def _prepare(db, lecturer, payload):
    unit = _owned_unit(db, payload.unit_id, lecturer.id)
    if unit is None:
        return None, None, None
    row = next((item for item in alerts.evaluate_unit(db, unit, "manual") if item["student"].id == payload.student_id), None)
    if row is None:
        return None, None, unit
    verdict = row["verdict"]
    return row, alerts.resolve_template(db, lecturer.id, verdict.final_tier if verdict else "high_risk", payload.template_id), unit


@router.post("/preview", response_model=PreviewOut)
def preview_alert(payload: SendRequest, db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    row, template, unit = _prepare(db, current_user, payload)
    if unit is None or row is None:
        raise HTTPException(status_code=404, detail="No such student in a unit you teach.")
    if template is None:
        raise HTTPException(status_code=400, detail="No template is available for this student's risk level.")
    student = row["student"]
    reason = row["blocked_reason"]
    # The preview has to render the acknowledgment footer too, using a
    # clearly fake token. Previewing without it would show the lecturer a
    # message shorter than the one their student receives - and a preview
    # that differs from the send is a preview that certifies nothing.
    # This token is never stored, so the link is inert by construction.
    context = {**row["context"], "acknowledge_url": alerts.acknowledge_url("preview-link-not-active")}
    body = ensure_acknowledgement(render(template.body, context), context["acknowledge_url"])
    return PreviewOut(student_id=student.id, unit_id=unit.id, recipient_email=student.email, recipient_name=student.name, subject=render(template.subject, context), body=body, template_id=template.id, template_name=template.name, eligible=row["eligible"], blocked_reason=reason, blocked_detail=alerts.BLOCKED_REASONS.get(reason) if reason else None)


@router.post("/send", response_model=SendResult)
def send_alert(payload: SendRequest, db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    row, template, unit = _prepare(db, current_user, payload)
    if unit is None or row is None:
        raise HTTPException(status_code=404, detail="No such student in a unit you teach.")
    if not row["eligible"]:
        raise HTTPException(status_code=400, detail=alerts.BLOCKED_REASONS.get(row["blocked_reason"], "This student cannot be alerted."))
    if template is None:
        raise HTTPException(status_code=400, detail="No template is available for this student's risk level.")
    alerts.queue_alert(db, row["student"], unit, row["lecturer"], row["verdict"], template, row["context"], "manual", current_user.id)
    db.commit()
    counts = alerts.drain_outbox(db, limit=5)
    return SendResult(queued=1, sent=counts["sent"], failed=counts["failed"])


@router.post("/send-bulk", response_model=SendResult)
def send_alerts_bulk(payload: BulkSendRequest, background: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    result = SendResult(queued=0, sent=0, failed=0, skipped={})
    for item in payload.items:
        row, template, unit = _prepare(db, current_user, item)
        if unit is None or row is None:
            key = "not_found"
        elif not row["eligible"]:
            key = row["blocked_reason"] or "not_eligible"
        elif template is None:
            key = "no_template"
        else:
            alerts.queue_alert(db, row["student"], unit, row["lecturer"], row["verdict"], template, row["context"], "manual", current_user.id)
            result.queued += 1
            continue
        result.skipped[key] = result.skipped.get(key, 0) + 1
    db.commit()
    if result.queued:
        background.add_task(_drain_in_background)
    return result


@router.get("/placeholders", response_model=list[PlaceholderOut])
def read_placeholders():
    return [PlaceholderOut(key=key, description=description) for key, description in PLACEHOLDERS.items()]


@router.get("/templates", response_model=list[TemplateOut])
def read_templates(db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    alerts.ensure_system_templates(db)
    rows = db.execute(select(EmailTemplate).where((EmailTemplate.lecturer_id == current_user.id) | EmailTemplate.is_system.is_(True)).order_by(EmailTemplate.is_system.desc(), EmailTemplate.risk_tier, EmailTemplate.name)).scalars().all()
    return [TemplateOut(id=row.id, name=row.name, risk_tier=row.risk_tier, subject=row.subject, body=row.body, is_system=row.is_system, updated_at=row.updated_at) for row in rows]


def _reject_unknown_placeholders(payload):
    unknown = unknown_placeholders(payload.subject, payload.body)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown placeholder{'s' if len(unknown) > 1 else ''}: " + ", ".join(f"{{{{{key}}}}}" for key in unknown))


def _template_out(template):
    return TemplateOut(id=template.id, name=template.name, risk_tier=template.risk_tier, subject=template.subject, body=template.body, is_system=template.is_system, updated_at=template.updated_at)


@router.post("/templates", response_model=TemplateOut, status_code=201)
def create_template(payload: TemplateSave, db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    _reject_unknown_placeholders(payload)
    template = EmailTemplate(lecturer_id=current_user.id, name=payload.name.strip(), risk_tier=payload.risk_tier, subject=payload.subject.strip(), body=payload.body, is_system=False)
    db.add(template); db.commit(); db.refresh(template)
    return _template_out(template)


@router.put("/templates/{template_id}", response_model=TemplateOut)
def update_template(payload: TemplateSave, template_id: int = Path(..., ge=1), db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    template = db.get(EmailTemplate, template_id)
    if template is None or (not template.is_system and template.lecturer_id != current_user.id):
        raise HTTPException(status_code=404, detail="No such template.")
    if template.is_system:
        raise HTTPException(status_code=400, detail="Built-in templates can't be edited. Save a copy instead.")
    _reject_unknown_placeholders(payload)
    template.name, template.risk_tier, template.subject, template.body = payload.name.strip(), payload.risk_tier, payload.subject.strip(), payload.body
    db.commit(); db.refresh(template)
    return _template_out(template)


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: int = Path(..., ge=1), db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    template = db.get(EmailTemplate, template_id)
    if template is None or (not template.is_system and template.lecturer_id != current_user.id):
        raise HTTPException(status_code=404, detail="No such template.")
    if template.is_system:
        raise HTTPException(status_code=400, detail="Built-in templates can't be deleted.")
    db.delete(template); db.commit()


@router.post("/run-sweep", response_model=SendResult)
def run_sweep_now(background: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(require_teaching_role())):
    summary = alerts.sweep_units(db, alerts.active_units(db, current_user.id))
    background.add_task(_drain_in_background)
    return SendResult(queued=summary["queued"], sent=0, failed=0, skipped=summary["skipped"])
