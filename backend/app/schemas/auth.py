"""
Pydantic schemas for the authentication domain - request/response
contracts for login and the current-user endpoint.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.enums import UserRole


# LOGIN REQUEST
class LoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        ...,
        min_length=8,
        max_length=64
    )



# TOKEN RESPONSE
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# TOKEN DATA (internal use)
class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None



# USER RESPONSE (/me endpoint)
class UserOut(BaseModel):
    """Public-facing User representation - excludes hashed_password."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


# CURRENT USER RESPONSE (/auth/me)
class MeOut(UserOut):
    """
    UserOut plus the one thing only the signed-in user needs to know
    about themselves: whether they hold a unit, and so whether the
    lecturer navigation belongs on their screen.

    A SUBCLASS used only by /auth/me, deliberately not a field added to
    UserOut itself. UserOut is also the row schema for
    `GET /admin/lecturers`, and putting `holds_units` there would fire
    one EXISTS query per row on every listing to answer a question that
    screen never asks - an N+1 introduced for a field nothing reads.
    """
    holds_units: bool