"""
JWT access token creation and verification.
Design:
- Stateless authentication (no refresh tokens in Phase 2)
- Role embedded for fast authorization
- Timezone-safe expiry handling
"""

from datetime import datetime, timedelta, timezone
from jose import jwt

from app.config import settings
from app.models.enums import UserRole


def create_access_token(user_id: int, role: UserRole) -> str:
    """
    Create a signed JWT access token for authenticated users.
    Claims:
        sub  -> user ID (JWT standard subject)
        role -> user role for RBAC (ADMIN / LECTURER / SUPER_ADMIN)
        exp  -> expiration timestamp
        iat  -> issued-at timestamp (audit/debug support)
    """

    now = datetime.now(timezone.utc)
    expire = now + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire,
        "iat": now
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """
    Decode and validate JWT token.

    Raises:
        jose.JWTError if token is invalid, expired, or tampered.

    Note:
        Do NOT suppress errors here. Higher layers (FastAPI dependency)
        will convert exceptions into HTTP 401 responses.
    """

    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )