##Authentication routes: login and current-user lookup.


from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.core.security import verify_password
from app.core.auth import create_access_token
from app.core.dependencies import get_current_user
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
@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user 