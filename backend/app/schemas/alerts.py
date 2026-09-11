"""Pydantic schemas for the Alerts page (Phase 7.8)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AlertCounters(BaseModel):
    total: int
    sent: int
    failed: int
    queued: int
    # Student alerts a student has confirmed receiving. Counted against
    # sent, never against total: a lecturer summary can never be
    # acknowledged, so "3 of 40" against total would be arithmetic that
    # can never reach 100%.
    acknowledged: int = 0
    acknowledgeable: int = 0


class AlertSummary(BaseModel):
    counters: AlertCounters
    unit_count: int
    checkpoint_week: int
    dry_run: bool
    outbox_path: Optional[str] = None


class QueueItem(BaseModel):
    student_id: int
    student_number: str
    name: str
    email: Optional[str] = None
    unit_id: int
    unit_code: str
    risk_tier: Optional[str] = None
    eligible: bool
    blocked_reason: Optional[str] = None
    blocked_detail: Optional[str] = None
    last_alert_at: Optional[datetime] = None
    last_alert_status: Optional[str] = None


class AlertQueue(BaseModel):
    ready: list[QueueItem] = []
    blocked: list[QueueItem] = []


class AlertLogItem(BaseModel):
    id: int
    kind: str
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    student_number: Optional[str] = None
    unit_code: Optional[str] = None
    recipient_email: str
    subject: str
    body: str
    template_name: Optional[str] = None
    risk_tier: Optional[str] = None
    trigger: str
    status: str
    error: Optional[str] = None
    attempts: int
    queued_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None


class AlertLogPage(BaseModel):
    items: list[AlertLogItem]
    total: int
    page: int
    page_size: int


class TemplateOut(BaseModel):
    id: int
    name: str
    risk_tier: str
    subject: str
    body: str
    is_system: bool
    updated_at: Optional[datetime] = None


class TemplateSave(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    risk_tier: Literal["safe", "low_risk", "high_risk"]
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)


class PlaceholderOut(BaseModel):
    key: str
    description: str


class SendRequest(BaseModel):
    student_id: int
    unit_id: int
    template_id: Optional[int] = None


class BulkSendRequest(BaseModel):
    items: list[SendRequest] = Field(min_length=1, max_length=200)


class PreviewOut(BaseModel):
    student_id: int
    unit_id: int
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    subject: str
    body: str
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    eligible: bool
    blocked_reason: Optional[str] = None
    blocked_detail: Optional[str] = None


class SendResult(BaseModel):
    queued: int
    sent: int
    failed: int
    skipped: dict[str, int] = {}
