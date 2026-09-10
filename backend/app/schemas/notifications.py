"""
The notification feed.

DERIVED, NOT STORED. Every item here is generated on read from a record
that already exists somewhere else - see notification_service.py. There
is no notifications table, so `id` is a COMPOSITE STRING, not a database
key: "ack:412", "batch:57", "audit:1093". It exists so React has a
stable key and so the frontend can deep-link without a second lookup.
Never treat it as a primary key; never let a client send it back.
"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel

NotificationKind = Literal[
    "alert_acknowledged",     # a student opened their alert
    "alert_failed",           # delivery failed
    "sweep_summary",          # the weekly sweep ran on your behalf
    "review_pending",         # students waiting on your decision
    "missing_data",           # students blocked on incomplete records
    "import_complete",        # a bulk upload finished
    "criteria_changed",       # a pass mark / unit shape changed
    "verdict_overridden",     # a lecturer overrode an engine verdict (admin)
    "unit_unassigned",        # a unit has no lecturer (admin)
    "unit_unconfigured",      # a unit has no criteria, so imports are blocked (admin)
]

Severity = Literal["info", "success", "warning", "critical"]

class NotificationItem(BaseModel):
    id: str
    kind: NotificationKind
    severity: Severity
    #: One line. Written server-side so the wording of a fact and the
    #: query that produced it live in the same file.
    title: str
    #: Optional second line - the unit code, a count, a reason.
    detail: Optional[str] = None
    occurred_at: datetime
    #: A frontend route. Server-supplied so a new kind ships with its
    #: destination rather than needing a matching switch in the client.
    link: Optional[str] = None
    unread: bool

class NotificationFeed(BaseModel):
    items: list[NotificationItem]
    unread_count: int
    seen_at: Optional[datetime] = None


class NotificationKindOption(BaseModel):
    key: NotificationKind
    label: str