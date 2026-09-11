"""Unauthenticated, token-scoped student self-service record."""

import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Path as PathParam, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.assessment_event import AssessmentEvent
from app.models.criteria import Criteria
from app.models.enrollment import Enrollment
from app.models.student_access import StudentAccessToken

router = APIRouter(tags=["Student - Portal"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
log = logging.getLogger("eduguard.student_portal")
_attempts: dict[str, tuple[float, int]] = {}
_WINDOW_SECONDS = 60
_MAX_REQUESTS = 20


def _limited(request: Request) -> bool:
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    started, count = _attempts.get(key, (now, 0))
    if now - started >= _WINDOW_SECONDS:
        started, count = now, 0
    count += 1
    _attempts[key] = (started, count)
    return count > _MAX_REQUESTS


@router.get("/portal/{token}", response_class=HTMLResponse)
def student_portal(
    request: Request,
    token: str = PathParam(..., min_length=20, max_length=128),
    db: Session = Depends(get_db),
):
    headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex, nofollow"}
    if _limited(request):
        log.warning("student portal rate limit exceeded host=%s", request.client.host if request.client else "unknown")
        return HTMLResponse("Too many requests. Please try again later.", status_code=429, headers=headers)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    access = db.execute(
        select(StudentAccessToken).where(
            StudentAccessToken.token_hash == digest,
            StudentAccessToken.expires_at > datetime.now(timezone.utc),
        )
    ).scalars().first()
    if access is None:
        log.info("student portal denied token_hash=%s", digest[:12])
        return HTMLResponse("This portal link is no longer available.", status_code=404, headers=headers)

    access.last_used_at = datetime.now(timezone.utc)
    db.commit()
    log.info("student portal accessed student_id=%s unit_id=%s", access.student_id, access.unit_id)
    criteria = db.execute(select(Criteria).where(Criteria.unit_id == access.unit_id, Criteria.enabled.is_(True)).order_by(Criteria.id)).scalars().all()
    events = db.execute(
        select(AssessmentEvent).where(
            AssessmentEvent.student_id == access.student_id,
            AssessmentEvent.unit_id == access.unit_id,
        ).order_by(AssessmentEvent.date.desc(), AssessmentEvent.id.desc())
    ).scalars().all()
    latest = {}
    for event in events:
        latest.setdefault(event.criteria_id, event)
    metrics, assessments = [], []
    for criterion in criteria:
        event = latest.get(criterion.id)
        if event is None:
            continue
        category = criterion.category.value if criterion.category else ""
        if category in ("attendance", "weekly_tut"):
            metrics.append({"label": criterion.name, "value": f"{round(event.score)}%"})
        elif category == "assessment":
            assessments.append({"name": criterion.name, "score": event.score, "threshold": criterion.threshold})
    return templates.TemplateResponse(
        request=request,
        name="portal.html",
        context={
            "student": access.student,
            "unit": access.unit,
            "metrics": metrics,
            "assessments": assessments,
            "interventions": [],
            "expires_at": access.expires_at.strftime("%d %B %Y"),
        },
        headers=headers,
    )
