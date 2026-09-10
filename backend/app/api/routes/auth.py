"""Authentication routes: login, current-user lookup, and account settings."""

import base64
import binascii
import re
from io import BytesIO
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AvatarUpload,
    LoginRequest,
    MeOut,
    PasswordChange,
    ProfileUpdate,
    TokenResponse,
    UserOut,
)
from app.schemas.preferences import Preferences, PreferencesUpdate
from app.core.security import hash_password, verify_password
from app.core.auth import create_access_token
from app.core.dependencies import get_current_user
from app.core.teaching import holds_active_unit
from app.models.login_attempt import LoginAttempt
from app.services.audit_service import client_ip
from sqlalchemy import func
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Authentication"])
_AVATAR_PREFIX = re.compile(r"^data:image/(png|jpeg|webp);base64,")
_MAX_AVATAR_BYTES = 60 * 1024
_MAX_AVATAR_DIMENSION = 512


# -------------------------
# LOGIN ENDPOINT
# -------------------------
@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, request: Request, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=15)
    email = str(credentials.email).strip().lower()
    ip = client_ip(request)
    email_failures = db.query(func.count(LoginAttempt.id)).filter(
        LoginAttempt.succeeded.is_(False),
        LoginAttempt.attempted_at >= since,
        LoginAttempt.email == email,
    ).scalar() or 0
    ip_failures = db.query(func.count(LoginAttempt.id)).filter(
        LoginAttempt.succeeded.is_(False),
        LoginAttempt.attempted_at >= since,
        LoginAttempt.ip == ip,
    ).scalar() or 0
    user = db.query(User).filter(User.email == credentials.email).first()
    # Always perform bcrypt work, including for locked/unknown accounts, to
    # keep lockout timing comparable with an ordinary failed login.
    valid_password = verify_password(
        credentials.password,
        user.hashed_password if user else "$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy",
    )
    locked = email_failures >= 5 or ip_failures >= 5
    attempt = LoginAttempt(email=email, ip=ip, succeeded=False, attempted_at=now)
    db.add(attempt)
    if locked:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": "900"},
        )
    # Generic error for unknown email OR wrong password.
    if not user or not valid_password:
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    # Only reached once the password is already proven correct, so this distinct message doesn't leak account status to a guesser.
    if not user.is_active:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )
    
    attempt.succeeded = True
    user.last_login = now
    db.commit()
    db.refresh(user)

    token = create_access_token(
        user_id=user.id,
        role=user.role
    )

    return TokenResponse(access_token=token)


# -------------------------
# GET CURRENT USER (/me)
# -------------------------
@router.get("/me", response_model=MeOut)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    The signed-in user, plus `holds_units`.

    `holds_units` is computed here rather than sent as a JWT claim on
    purpose. A token lives for hours; unit assignment changes in a
    second. Baking it into the token would leave an admin who was just
    given a unit staring at an admin panel until their token expired,
    and an admin whose last unit was archived holding a lecturer nav
    whose every endpoint now returns nothing.

    It is the ONE extra query on this endpoint, EXISTS-shaped, and the
    frontend caches the result for the session - see refreshUser() in
    AuthContext for how it is re-read after an assignment changes.
    """
    return _me_out(current_user, db)


def _me_out(user: User, db: Session) -> MeOut:
    return MeOut(
        **UserOut.model_validate(user).model_dump(),
        holds_units=holds_active_unit(db, user.id),
        preferences=Preferences(**(user.preferences or {})),
    )


@router.patch("/me/profile", response_model=MeOut)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    normalized_name = " ".join(payload.full_name.split())
    if not normalized_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Full name must not be blank",
        )

    current_user.full_name = normalized_name
    db.commit()
    db.refresh(current_user)
    return _me_out(current_user, db)



@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    current_user.hashed_password = hash_password(payload.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/me/avatar", response_model=MeOut)
def upload_avatar(
    payload: AvatarUpload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = _AVATAR_PREFIX.match(payload.data_url)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Avatar must be a PNG, JPEG, or WebP data URL",
        )

    encoded = payload.data_url[match.end():]
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Avatar data is not valid base64",
        )

    if len(image_bytes) > _MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Avatar image must be 60 KB or smaller",
        )

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
        with Image.open(BytesIO(image_bytes)) as image:
            if (
                image.width > _MAX_AVATAR_DIMENSION
                or image.height > _MAX_AVATAR_DIMENSION
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Avatar dimensions must not exceed 512x512 pixels",
                )
            image.load()
            mode = "RGBA" if "A" in image.getbands() else "RGB"
            converted = image.convert(mode)
            output = BytesIO()
            converted.save(output, format="WEBP")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Avatar data is not a valid image",
        )

    current_user.avatar = (
        "data:image/webp;base64,"
        + base64.b64encode(output.getvalue()).decode("ascii")
    )
    db.commit()
    db.refresh(current_user)
    return _me_out(current_user, db)


@router.delete("/me/avatar", response_model=MeOut)
def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.avatar = None
    db.commit()
    db.refresh(current_user)
    return _me_out(current_user, db)


@router.patch("/me/preferences", response_model=MeOut)
def update_preferences(
    payload: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    merged = {
        **(current_user.preferences or {}),
        **payload.model_dump(exclude_unset=True),
    }
    try:
        validated = Preferences.model_validate(merged)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )

    current_user.preferences = validated.model_dump()
    db.commit()
    db.refresh(current_user)
    return _me_out(current_user, db)