"""Pydantic schemas for the audit log."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditActionOut(BaseModel):
    """One entry in the action vocabulary, for the filter dropdown."""

    key: str
    label: str
    description: str


class AuditEventOut(BaseModel):
    id: int
    occurred_at: Optional[datetime] = None
    action: str
    action_label: str

    #: NULL only if the account was deleted after the act. The captured
    #: name and email below survive that, which is the point of storing
    #: them separately.
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None

    unit_id: Optional[int] = None
    unit_code: Optional[str] = None
    student_id: Optional[int] = None
    student_name: Optional[str] = None

    entity_type: Optional[str] = None
    entity_id: Optional[int] = None

    #: A finished sentence written where the change happened. The table
    #: prints this; it does not rebuild it from the two snapshots.
    summary: str
    #: Raw JSON text, shown only when a row is expanded. Kept as a string
    #: rather than parsed into a model because the four actions carry
    #: four different shapes, and a schema that accepted all of them
    #: would validate none of them.
    before_state: Optional[str] = None
    after_state: Optional[str] = None

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditEventPage(BaseModel):
    items: list[AuditEventOut]
    total: int
    page: int
    page_size: int