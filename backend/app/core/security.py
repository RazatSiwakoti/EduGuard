"""
Password hashing utilities.

Uses bcrypt (cost factor 12) via passlib. This module only knows how to hash and verify - it has no knowledge of FastAPI, the database, or
JWTs, so it can be tested and reused in isolation.

Password length policy (8-64 chars) is enforced at the schema layer (app/schemas/auth.py), not here - keeping that rule in one place only
avoids it drifting out of sync between two files.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password for storage. Never store the plaintext itself."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a login attempt's password against the stored hash. Returns True/False."""
    return pwd_context.verify(plain_password, hashed_password)