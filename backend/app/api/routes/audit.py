"""
Reading the audit log. Admin and super-admin only.

READ-ONLY, AND THERE IS NO OTHER VERB HERE ON PURPOSE.
No POST, no PATCH, no DELETE. A log with an edit endpoint is a document,
not a record - the moment the application can rewrite its own history,
every row in it becomes a claim rather than evidence. Rows are written
only as a side effect of the act they describe, in the same transaction,
by `audit_service.record`.

WHY LECTURERS CANNOT READ IT.
Oversight is the whole purpose. A log of who changed what, readable by
everyone whose changes it records, is a log people manage rather than a
log people are accountable to. Lecturers see their own work everywhere
else in the system; this one view exists for the person checking it.

WHY ADMINS SEE EVERY UNIT, NOT ONLY THEIR OWN.
An admin who also teaches is scoped to their own units everywhere in the
lecturer surface, and the temptation is to scope this the same way. It
would defeat the feature: the acts most worth reviewing are the ones the
reviewer did not perform. The trade is real and is stated rather than
hidden - an admin here can see that a colleague lowered a pass mark on a
unit they have nothing to do with. In an institution the correct answer
is a separate auditor role; with three roles, oversight sits with admin.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database import get_db
from app.models.enums import UserRole
from app.schemas.audit import AuditActionOut, AuditEventOut, AuditEventPage
from app.services import audit_service

router = APIRouter(
    prefix="/admin/audit",
    tags=["Admin - Audit log"],
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)


@router.get("/actions", response_model=list[AuditActionOut])
def read_actions():
    """
    The closed vocabulary, with a sentence explaining each.

    Served from the server rather than hardcoded in the client so a new
    action appears in the filter the day it starts being recorded, and
    so the explanation of what an action MEANS lives beside the constant
    that names it.
    """
    return [
        AuditActionOut(
            key=key,
            label=label,
            description=audit_service.ACTION_DESCRIPTIONS.get(key, ""),
        )
        for key, label in audit_service.ACTION_LABELS.items()
    ]


@router.get("", response_model=AuditEventPage)
def read_events(
    action: Optional[str] = Query(default=None),
    unit_id: Optional[int] = Query(default=None, ge=1),
    actor_id: Optional[int] = Query(default=None, ge=1),
    days: Optional[int] = Query(default=None, ge=1, le=3650),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Newest first. Every filter is optional and they combine."""
    rows, total = audit_service.list_events(
        db,
        action=action,
        unit_id=unit_id,
        actor_id=actor_id,
        days=days,
        search=search,
        page=page,
        page_size=page_size,
    )

    return AuditEventPage(
        items=[
            AuditEventOut(
                id=row.id,
                occurred_at=row.occurred_at,
                action=row.action,
                # Resolved here, not stored on the row. A label is
                # presentation: freezing it into the table would mean
                # renaming one required rewriting history.
                action_label=audit_service.ACTION_LABELS.get(row.action, row.action),
                actor_id=row.actor_id,
                actor_name=row.actor_name,
                actor_email=row.actor_email,
                actor_role=row.actor_role,
                unit_id=row.unit_id,
                unit_code=row.unit_code,
                student_id=row.student_id,
                student_name=row.student_name,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                summary=row.summary,
                before_state=row.before_state,
                after_state=row.after_state,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )