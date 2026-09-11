"""Enumeration-resistant, single-use password reset flow."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.email_message import EmailMessage
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.schemas.auth import PasswordResetConfirm, PasswordResetRequest
from app.core.security import hash_password
from app.services.audit_service import client_ip

router = APIRouter(prefix="/auth/password-reset", tags=["Authentication"])


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/request", status_code=status.HTTP_204_NO_CONTENT)
def request_reset(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(payload.email).strip().lower()).first()
    if user:
        raw_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({"used_at": now}, synchronize_session=False)
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=_hash(raw_token),
            expires_at=now + timedelta(minutes=30),
            created_ip=client_ip(request),
        ))
        link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={raw_token}"
        db.add(EmailMessage(
            kind="password_reset",
            lecturer_id=user.id,
            recipient_email=user.email,
            recipient_name=user.full_name,
            subject="EduGuard password reset",
            body=f"Use this link to reset your EduGuard password (valid for 30 minutes):\n\n{link}\n\nIf you did not request this, ignore this email.",
            trigger="manual",
            status="queued",
            created_by=user.id,
        ))
        db.commit()
    else:
        db.rollback()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == _hash(payload.token),
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > now,
    ).first()
    if not reset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset link is invalid or expired")
    reset.user.hashed_password = hash_password(payload.new_password)
    reset.user.password_changed_at = now
    reset.used_at = now
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == reset.user_id,
        PasswordResetToken.id != reset.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
