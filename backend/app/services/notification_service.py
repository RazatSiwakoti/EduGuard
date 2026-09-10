"""Build the derived notification feed from existing EduGuard records."""

from datetime import date, datetime, time, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.teaching import uses_lecturer_surface
from app.models.audit_event import AuditEvent
from app.models.criteria import Criteria
from app.models.email_message import EmailMessage
from app.models.enums import CriteriaCategory, UserRole
from app.models.final_verdicts import FinalVerdict
from app.models.ingestion_batch import IngestionBatch
from app.models.intervention import Intervention
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User
from app.schemas.notifications import NotificationItem
from app.services.audit_service import (
    ACTION_LABELS,
    CRITERIA_SHAPE_REPLACED,
    CRITERIA_UNLOCKED,
    THRESHOLD_CHANGED,
    VERDICT_OVERRIDDEN,
)

NOTIFICATION_KIND_LABELS = {
    "alert_acknowledged": "Acknowledged alerts",
    "alert_failed": "Failed alerts",
    "sweep_summary": "Sweep summaries",
    "review_pending": "Review pending",
    "missing_data": "Missing data",
    "import_complete": "Data imports",
    "criteria_changed": "Criteria changes",
    "verdict_overridden": "Verdict overrides",
    "unit_unassigned": "Unassigned units",
    "unit_unconfigured": "Unconfigured units",
    "follow_up_due": "Follow-ups due",
}


def build_feed(db: Session, user: User, limit: int) -> list[NotificationItem]:
    """Build, mark, sort, and cap the current user's notification feed."""
    items: list[NotificationItem] = []

    if uses_lecturer_surface(db, user):
        items.extend(_acknowledgments(db, user))
        items.extend(_failed_alerts(db, user))
        items.extend(_sweep_summaries(db, user))
        items.extend(_review_pending(db, user))
        items.extend(_missing_data(db, user))
        items.extend(_imports(db, user))
        items.extend(_criteria_changes(db, user))
        items.extend(_follow_ups_due(db, user))

    if user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        items.extend(_unassigned_units(db))
        items.extend(_unconfigured_units(db))
        items.extend(_overrides(db, user))

    items.sort(key=lambda item: item.occurred_at, reverse=True)
    seen_at = user.notifications_seen_at
    for item in items:
        item.unread = _is_unread(item.occurred_at, seen_at)
    return items[: max(0, limit)]


def _is_unread(occurred_at: datetime, seen_at: datetime | None) -> bool:
    if seen_at is None:
        return True
    if occurred_at.tzinfo is None and seen_at.tzinfo is not None:
        seen_at = seen_at.replace(tzinfo=None)
    elif occurred_at.tzinfo is not None and seen_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=None)
    return occurred_at > seen_at


def _acknowledgments(db: Session, user: User) -> list[NotificationItem]:
    rows = db.execute(
        select(EmailMessage, Student.name, Unit)
        .join(Student, Student.id == EmailMessage.student_id)
        .join(Unit, Unit.id == EmailMessage.unit_id)
        .where(
            EmailMessage.lecturer_id == user.id,
            EmailMessage.kind == "student_alert",
            EmailMessage.acknowledged_at.is_not(None),
        )
        .order_by(EmailMessage.acknowledged_at.desc(), EmailMessage.id.desc())
        .limit(10)
    ).all()
    return [
        NotificationItem(
            id=f"ack:{message.id}",
            kind="alert_acknowledged",
            severity="success",
            title=f"{student_name} opened their alert",
            detail=f"{unit.full_code} · {message.risk_tier or 'risk level unavailable'}",
            occurred_at=message.acknowledged_at,
            link=f"/students?student={message.student_id}&cardUnit={message.unit_id}",
            unread=False,
        )
        for message, student_name, unit in rows
    ]


def _failed_alerts(db: Session, user: User) -> list[NotificationItem]:
    count, occurred_at = db.execute(
        select(func.count(EmailMessage.id), func.max(EmailMessage.queued_at)).where(
            EmailMessage.lecturer_id == user.id,
            EmailMessage.kind == "student_alert",
            EmailMessage.status == "failed",
        )
    ).one()
    if not count:
        return []
    return [
        NotificationItem(
            id=f"failed-alerts:{user.id}",
            kind="alert_failed",
            severity="critical",
            title=f"{count} alert{'s' if count != 1 else ''} could not be delivered",
            occurred_at=occurred_at or datetime.now(timezone.utc),
            link="/alerts",
            unread=False,
        )
    ]


def _sweep_summaries(db: Session, user: User) -> list[NotificationItem]:
    rows = db.execute(
        select(EmailMessage)
        .where(
            EmailMessage.lecturer_id == user.id,
            EmailMessage.kind == "lecturer_summary",
        )
        .order_by(EmailMessage.queued_at.desc(), EmailMessage.id.desc())
        .limit(3)
    ).scalars().all()
    return [
        NotificationItem(
            id=f"summary:{message.id}",
            kind="sweep_summary",
            severity="info",
            title=message.subject,
            occurred_at=message.queued_at,
            link="/alerts",
            unread=False,
        )
        for message in rows
    ]


def _verdict_rows(db: Session, user: User, *, missing: bool) -> list[FinalVerdict]:
    return db.execute(
        select(FinalVerdict)
        .join(Unit, Unit.id == FinalVerdict.unit_id)
        .where(
            Unit.lecturer_id == user.id,
            FinalVerdict.is_missing_data.is_(missing),
            FinalVerdict.requires_review.is_(True) if not missing else True,
        )
        .order_by(FinalVerdict.created_at.desc(), FinalVerdict.id.desc())
    ).scalars().all()


def _review_pending(db: Session, user: User) -> list[NotificationItem]:
    rows = _verdict_rows(db, user, missing=False)
    if not rows:
        return []
    count = len({row.student_id for row in rows})
    return [
        NotificationItem(
            id=f"review-pending:{user.id}",
            kind="review_pending",
            severity="warning",
            title=f"{count} student{'s' if count != 1 else ''} require your review",
            occurred_at=rows[0].created_at,
            link="/students?bucket=needs_review",
            unread=False,
        )
    ]


def _missing_data(db: Session, user: User) -> list[NotificationItem]:
    rows = db.execute(
        select(FinalVerdict)
        .join(Unit, Unit.id == FinalVerdict.unit_id)
        .where(
            Unit.lecturer_id == user.id,
            FinalVerdict.is_missing_data.is_(True),
        )
        .order_by(FinalVerdict.created_at.desc(), FinalVerdict.id.desc())
    ).scalars().all()
    if not rows:
        return []
    count = len({row.student_id for row in rows})
    return [
        NotificationItem(
            id=f"missing-data:{user.id}",
            kind="missing_data",
            severity="warning",
            title=f"{count} student{'s are' if count != 1 else ' is'} blocked by missing data",
            occurred_at=rows[0].created_at,
            link="/students?bucket=needs_review",
            unread=False,
        )
    ]


def _imports(db: Session, user: User) -> list[NotificationItem]:
    rows = db.execute(
        select(IngestionBatch, Unit)
        .join(Unit, Unit.id == IngestionBatch.unit_id)
        .where(IngestionBatch.lecturer_id == user.id)
        .order_by(IngestionBatch.uploaded_at.desc(), IngestionBatch.id.desc())
        .limit(5)
    ).all()
    return [
        NotificationItem(
            id=f"batch:{batch.id}",
            kind="import_complete",
            severity="warning" if batch.values_failed else "success",
            title=(
                f"Import recorded {batch.values_stored} values with "
                f"{batch.values_failed} error{'s' if batch.values_failed != 1 else ''}"
                if batch.values_failed
                else f"Imported {batch.total_rows} rows"
            ),
            detail=unit.full_code,
            occurred_at=batch.uploaded_at,
            link=f"/units/{batch.unit_id}",
            unread=False,
        )
        for batch, unit in rows
    ]


def _criteria_changes(db: Session, user: User) -> list[NotificationItem]:
    actions = (THRESHOLD_CHANGED, CRITERIA_UNLOCKED, CRITERIA_SHAPE_REPLACED)
    rows = db.execute(
        select(AuditEvent)
        .join(Unit, Unit.id == AuditEvent.unit_id)
        .where(
            Unit.lecturer_id == user.id,
            AuditEvent.action.in_(actions),
            or_(AuditEvent.actor_id.is_(None), AuditEvent.actor_id != user.id),
        )
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .limit(10)
    ).scalars().all()
    return [
        NotificationItem(
            id=f"audit:{event.id}",
            kind="criteria_changed",
            severity="info",
            title=f"{ACTION_LABELS[event.action]} · {event.unit_code}",
            occurred_at=event.occurred_at,
            link=f"/units/{event.unit_id}",
            unread=False,
        )
        for event in rows
        if event.action in ACTION_LABELS
    ]


def _follow_ups_due(db: Session, user: User) -> list[NotificationItem]:
    rows = db.execute(
        select(Intervention, Student.name, Unit)
        .join(Student, Student.id == Intervention.student_id)
        .join(Unit, Unit.id == Intervention.unit_id)
        .where(
            Intervention.lecturer_id == user.id,
            Intervention.follow_up_on <= date.today(),
        )
        .order_by(Intervention.follow_up_on.asc(), Intervention.id.asc())
        .limit(20)
    ).all()
    return [
        NotificationItem(
            id=f"follow-up:{intervention.id}",
            kind="follow_up_due",
            severity="warning",
            title=f"Follow-up due for {student_name}",
            detail=f"{unit.full_code} · {intervention.kind}",
            occurred_at=datetime.combine(
                intervention.follow_up_on, time.min, tzinfo=timezone.utc
            ),
            link=f"/students?student={intervention.student_id}&cardUnit={intervention.unit_id}",
            unread=False,
        )
        for intervention, student_name, unit in rows
    ]


def _unassigned_units(db: Session) -> list[NotificationItem]:
    count = db.execute(
        select(func.count(Unit.id)).where(
            Unit.is_active.is_(True),
            Unit.lecturer_id.is_(None),
        )
    ).scalar_one()
    if not count:
        return []
    return [
        NotificationItem(
            id="unassigned-units",
            kind="unit_unassigned",
            severity="warning",
            title=f"{count} active unit{'s have' if count != 1 else ' has'} no lecturer",
            occurred_at=datetime.now(timezone.utc),
            link="/admin",
            unread=False,
        )
    ]


def _unconfigured_units(db: Session) -> list[NotificationItem]:
    fixed_categories = (CriteriaCategory.ATTENDANCE.value, CriteriaCategory.MOODLE.value)
    units = db.execute(
        select(Unit)
        .where(Unit.is_active.is_(True))
        .where(
            ~select(Criteria.id)
            .where(
                Criteria.unit_id == Unit.id,
                Criteria.enabled.is_(True),
                or_(
                    Criteria.category.is_(None),
                    ~Criteria.category.in_(fixed_categories),
                ),
            )
            .exists()
        )
    ).scalars().all()
    if not units:
        return []
    return [
        NotificationItem(
            id=f"unconfigured-unit:{unit.id}",
            kind="unit_unconfigured",
            severity="warning",
            title=f"{unit.full_code} is unconfigured",
            occurred_at=datetime.now(timezone.utc),
            detail="Only fixed attendance and Moodle criteria are enabled",
            link="/admin",
            unread=False,
        )
        for unit in units
    ]


def _overrides(db: Session, user: User) -> list[NotificationItem]:
    rows = db.execute(
        select(AuditEvent)
        .where(
            AuditEvent.action == VERDICT_OVERRIDDEN,
            or_(AuditEvent.actor_id.is_(None), AuditEvent.actor_id != user.id),
        )
        .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .limit(5)
    ).scalars().all()
    return [
        NotificationItem(
            id=f"audit:{event.id}",
            kind="verdict_overridden",
            severity="info",
            title=f"{event.actor_name or event.actor_email or 'A user'} overrode a verdict",
            detail=event.unit_code,
            occurred_at=event.occurred_at,
            link="/admin#audit",
            unread=False,
        )
        for event in rows
    ]