"""
Writing and reading the audit log.

THE WRITE STAGES, IT DOES NOT COMMIT.
`record()` calls `db.add()` and stops. The route that made the change
owns the commit, so the audit row and the change it describes land in
ONE transaction. That is the whole design:

  * commit the audit row separately and a rolled-back change leaves a
    log entry describing something that never happened
  * write it after the commit and a crash in between leaves a change
    with no record of who made it

Both failures are worse than no log, because both produce a log a reader
would be right to trust and wrong to believe.

RECORDING NEVER BREAKS THE FEATURE IT OBSERVES.
`record()` catches its own exceptions and reports the failure through
the logger rather than raising. A lecturer must not be unable to lower a
pass mark because an audit column was renamed. This is a deliberate
trade in the other direction from a compliance system, where the correct
behaviour is to refuse the action - said plainly here so the choice is
visible rather than accidental. If EduGuard is ever operated somewhere
that must not lose an event, this is the function to invert.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent
from app.models.student import Student
from app.models.unit import Unit
from app.models.user import User

logger = logging.getLogger("eduguard.audit")


# ---------------------------------------------------------------------
# The vocabulary
#
# A closed set, defined in one place. An audit log whose `action` column
# is free text drifts into "threshold_changed", "threshold.changed" and
# "Threshold Changed" within a month, and every filter over it silently
# under-reports from then on.
# ---------------------------------------------------------------------

THRESHOLD_CHANGED = "threshold.changed"
CRITERIA_UNLOCKED = "criteria.unlocked"
CRITERIA_SHAPE_REPLACED = "criteria.shape_replaced"
VERDICT_OVERRIDDEN = "verdict.overridden"

ACTION_LABELS: dict[str, str] = {
    THRESHOLD_CHANGED: "Pass mark changed",
    CRITERIA_UNLOCKED: "Unit shape unlocked",
    CRITERIA_SHAPE_REPLACED: "Unit shape replaced",
    VERDICT_OVERRIDDEN: "Verdict overridden",
}

ACTION_DESCRIPTIONS: dict[str, str] = {
    THRESHOLD_CHANGED:
        "A lecturer moved the pass mark for a category, which changes which "
        "students the engines call at risk.",
    CRITERIA_UNLOCKED:
        "An admin opened a one-shot window to edit a unit whose shape was "
        "locked because results already existed.",
    CRITERIA_SHAPE_REPLACED:
        "A coordinator replaced a unit's assessments or tutorial setting, "
        "which changes what every stored score means.",
    VERDICT_OVERRIDDEN:
        "A lecturer decided an engine disagreement, setting a student's final "
        "tier by hand.",
}


def _dump(value: Any) -> Optional[str]:
    """Serialises a before/after snapshot, never raising on odd types."""
    if value is None:
        return None
    try:
        return json.dumps(value, default=str, sort_keys=True)
    except Exception:  # noqa: BLE001 - a snapshot must not break a write
        return json.dumps({"unserialisable": str(type(value))})


def client_ip(request) -> Optional[str]:
    """
    The peer address of the connection, and nothing else.

    X-Forwarded-For is deliberately ignored. It is set by the caller, so
    honouring it without a configured list of trusted proxies lets the
    one field meant to identify where an action came from be forged by
    the person taking the action. Behind a reverse proxy this records
    the proxy - which is true, if less useful, and true beats useful in
    an audit log.
    """
    if request is None or getattr(request, "client", None) is None:
        return None
    return request.client.host


def user_agent(request) -> Optional[str]:
    if request is None:
        return None
    # Truncated: this string is attacker-controlled and unbounded, and an
    # audit table is not the place to store a megabyte of someone's
    # header.
    return (request.headers.get("user-agent") or "")[:400] or None


def record(
    db: Session,
    *,
    action: str,
    actor: Optional[User],
    summary: str,
    unit: Optional[Unit] = None,
    student: Optional[Student] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    before: Any = None,
    after: Any = None,
    request=None,
) -> Optional[AuditEvent]:
    """
    Stages one audit row. Returns it, or None if recording failed.

    The caller commits. See the module docstring for why that is not
    negotiable.
    """
    try:
        event = AuditEvent(
            action=action,
            actor_id=actor.id if actor else None,
            actor_email=(actor.email if actor else None),
            actor_name=(actor.full_name if actor else None),
            actor_role=(actor.role.value if actor and hasattr(actor.role, "value") else (str(actor.role) if actor else None)),
            unit_id=unit.id if unit else None,
            unit_code=unit.unit_code if unit else None,
            student_id=student.id if student else None,
            student_name=student.name if student else None,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            before_state=_dump(before),
            after_state=_dump(after),
            ip_address=client_ip(request),
            user_agent=user_agent(request),
        )
        db.add(event)
        return event
    except Exception:  # noqa: BLE001 - see the module docstring
        logger.exception("could not record audit event %r", action)
        return None


# ---------------------------------------------------------------------
# Threshold snapshots
#
# `lecturer_threshold_view` returns a dict carrying more than the pass
# marks. Storing the whole thing on both sides would make every row a
# wall of JSON in which the two numbers that changed are invisible, so
# the snapshot is reduced to the pass marks and the diff is computed
# from it.
# ---------------------------------------------------------------------

def threshold_snapshot(view: dict) -> dict[str, list[float]]:
    """
    Reduces a threshold view to {category: [distinct pass marks]}.

    A LIST, not a number, and that is the point. `threshold` is stored
    per criterion while the form shows one slider per category, so a
    unit can genuinely sit at 46 and 50 at once - `threshold_group`
    reports that as `mixed`. Saving flattens both to one value, and a
    snapshot that recorded only the first would make the audit log say
    "50% to 45%" about an act that also silently moved a 46. The list
    records what was actually flattened.
    """
    return {
        str(key): [float(value) for value in (group.get("values") or [])]
        for key, group in ((view or {}).get("thresholds") or {}).items()
        if group
    }


def _format_marks(values: list[float]) -> str:
    if not values:
        return "not set"
    if len(values) == 1:
        return f"{values[0]:g}%"
    return "mixed (" + ", ".join(f"{value:g}%" for value in values) + ")"


def describe_threshold_change(before: dict, after: dict) -> str:
    """
    A sentence naming every bar that moved, and what it moved from.

    Returns "" when nothing moved, which is the caller's signal not to
    write a row at all. The threshold form GETs the values and PATCHes
    them back, so a lecturer who opens a unit and presses Save has sent
    the stored numbers - recording that as a change would fill the log
    with acts nobody performed, and a log full of non-events is one
    nobody reads.
    """
    parts = [
        f"{key.replace('_', ' ')} {_format_marks(before.get(key, []))} "
        f"to {_format_marks(after[key])}"
        for key in sorted(after)
        if before.get(key, []) != after[key]
    ]
    if not parts:
        return ""
    return "Pass mark changed: " + "; ".join(parts) + "."


def shape_snapshot(shape: dict) -> dict:
    """
    Reduces a unit shape to the fields a reader is reconstructing.

    The full payload carries limits, lock state and derived totals -
    none of which the coordinator chose. Storing them on both sides
    would bury the two rows that actually changed in JSON the reader has
    to skip past.
    """
    return {
        "assessments": [
            {
                "name": item.get("name"),
                "percentage": item.get("percentage"),
                "max_score": item.get("max_score"),
                "threshold": item.get("threshold"),
            }
            for item in ((shape or {}).get("assessments") or [])
        ],
        "tutorials_enabled": (shape or {}).get("tutorials_enabled"),
        "total_percentage": (shape or {}).get("total_percentage"),
    }


def describe_shape_change(before: dict, after: dict) -> str:
    """A sentence for a shape replace, naming what actually moved."""
    before_names = [item["name"] for item in before.get("assessments", [])]
    after_names = [item["name"] for item in after.get("assessments", [])]

    parts: list[str] = []
    if before_names != after_names:
        parts.append(
            f"assessments {', '.join(before_names) or 'none'} "
            f"to {', '.join(after_names) or 'none'}"
        )
    else:
        for was, now in zip(before.get("assessments", []), after.get("assessments", [])):
            if was != now:
                parts.append(
                    f"{now['name']} {was.get('percentage')}% to {now.get('percentage')}%"
                )
    if before.get("tutorials_enabled") != after.get("tutorials_enabled"):
        parts.append(
            "weekly tutorial " + ("enabled" if after.get("tutorials_enabled") else "disabled")
        )

    if not parts:
        return ""
    return "Unit shape replaced: " + "; ".join(parts) + "."


# ---------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------

def list_events(
    db: Session,
    *,
    action: Optional[str] = None,
    unit_id: Optional[int] = None,
    actor_id: Optional[int] = None,
    days: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[AuditEvent], int]:
    """Newest first, filtered, paginated. Returns (rows, total)."""
    stmt = select(AuditEvent)

    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if unit_id is not None:
        stmt = stmt.where(AuditEvent.unit_id == unit_id)
    if actor_id is not None:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if days is not None and days > 0:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        stmt = stmt.where(AuditEvent.occurred_at >= cutoff)

    needle = (search or "").strip().lower()
    if needle:
        pattern = f"%{needle}%"
        stmt = stmt.where(
            AuditEvent.summary.ilike(pattern)
            | AuditEvent.actor_email.ilike(pattern)
            | AuditEvent.actor_name.ilike(pattern)
            | AuditEvent.unit_code.ilike(pattern)
            | AuditEvent.student_name.ilike(pattern)
        )

    rows = db.execute(
        stmt.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
    ).scalars().all()

    start = max(0, (page - 1) * page_size)
    return list(rows[start:start + page_size]), len(rows)