"""
Authorization dependencies: identifies the current user from a JWT,
and gates routes by role.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.database import get_db
from app.core.auth import decode_access_token
from app.models.user import User
from app.models.enums import UserRole
from app.core.teaching import TEACHING_ROLES

# tokenUrl only tells Swagger where the "Authorize" flow would post
# to - it doesn't force /auth/login to accept form-encoded data.
oauth2_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )

    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-gated routes.
    Usage: @router.get(..., dependencies=[Depends(require_role(UserRole.ADMIN))])
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker


# ---------------------------------------------------------------------
# Teaching surface (T5)
# ---------------------------------------------------------------------


def require_teaching_role():
    """
    Gate for every lecturer-facing endpoint.

    ADMIN is allowed through alongside LECTURER because an admin may
    also hold a unit. This widens the ROLE gate ONLY, and it is safe
    precisely because not one lecturer endpoint decides what you may
    see from your role - every one of them scopes on
    `Unit.lecturer_id == current_user.id` taken from the validated JWT.
    An admin with no units therefore reaches these endpoints and gets
    empty lists, the same answer a brand-new lecturer gets; an admin
    with units sees exactly their own and nobody else's.

    A named dependency rather than `require_role(LECTURER, ADMIN)`
    written out forty times: the reason lives in one docstring, and the
    day a fourth role teaches, one line changes instead of forty.
    """
    return require_role(*TEACHING_ROLES)