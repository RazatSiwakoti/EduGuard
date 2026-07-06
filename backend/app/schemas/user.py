"""
Pydantic schemas for user management (creating Admins and Lecturers).

UserOut is intentionally NOT redefined here - it already exists in
app.schemas.auth and is reused as-is, so there's exactly one definition
of "what a User looks like in a response" rather than two that could
drift apart.
"""

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """
    Used for both Admin and Lecturer creation. Role is deliberately absent -
    it's hardcoded server-side per endpoint (Super Admin routes always create
    an ADMIN, Admin routes always create a LECTURER), never trusted from the
    request body.
    """
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=64)