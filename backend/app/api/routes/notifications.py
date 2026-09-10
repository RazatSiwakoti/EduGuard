"""Authenticated notification feed endpoints."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.notifications import NotificationFeed, NotificationKind, NotificationKindOption
from app.services.notification_service import NOTIFICATION_KIND_LABELS, build_feed


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=NotificationFeed)
def read_notifications(
    limit: int = Query(default=6, ge=1, le=50),
    kind: Optional[NotificationKind] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationFeed:
    """Return the newest relevant notifications without changing seen state."""
    # Build the largest allowed feed before filtering so a kind filter does
    # not hide matching records that fall outside the default bell limit.
    items = build_feed(db, current_user, 50)
    if kind is not None:
        items = [item for item in items if item.kind == kind]
    items = items[:limit]
    return NotificationFeed(
        items=items,
        unread_count=sum(item.unread for item in items),
        seen_at=current_user.notifications_seen_at,
    )


@router.get("/kinds", response_model=list[NotificationKindOption])
def read_notification_kinds() -> list[NotificationKindOption]:
    """Return the server-owned notification filter vocabulary."""
    return [
        NotificationKindOption(key=key, label=label)
        for key, label in NOTIFICATION_KIND_LABELS.items()
    ]


@router.post("/seen", status_code=status.HTTP_204_NO_CONTENT)
def mark_notifications_seen(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Mark the current user's feed as seen; GET never performs this write."""
    current_user.notifications_seen_at = datetime.now(timezone.utc)
    db.add(current_user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)