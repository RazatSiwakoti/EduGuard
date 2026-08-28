##Authentication routes: login and current-user lookup.


from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, MeOut, TokenResponse, UserOut
from app.core.security import verify_password
from app.core.auth import create_access_token
from app.core.dependencies import get_current_user
from app.core.teaching import holds_active_unit
router = APIRouter(prefix="/auth", tags=["Authentication"])


# -------------------------
# LOGIN ENDPOINT
# -------------------------
@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == credentials.email).first()
# Generic error for unknown email OR wrong password - checked together so a wrong password never confirms whether an email
# exists in the system (account enumeration protection).
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Only reached once the password is already proven correct, so this distinct message doesn't leak account status to a guesser.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )
    
    user.last_login = datetime.now(timezone.utc)
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
    return MeOut(
        **UserOut.model_validate(current_user).model_dump(),
        holds_units=holds_active_unit(db, current_user.id),
    )