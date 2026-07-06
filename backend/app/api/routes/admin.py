"""
Admin routes: manage Lecturer accounts only.

Strict silo, same as Super Admin - an Admin manages Lecturer lifecycles here. Unit management lives in its own route module even though it's
also Admin-only, so this file stays focused on the User/Lecturer domain.

The placeholder "deleted user" account (see app.core.system_accounts) has role=LECTURER, so it's explicitly excluded from listings and from
being targeted by id - it should never appear as a real account.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.auth import UserOut
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.core.dependencies import require_role
from app.core.system_accounts import PLACEHOLDER_USER_EMAIL
from app.services import account_service

router = APIRouter(
    prefix="/admin",
    tags=["Admin - Lecturers"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


def _get_lecturer_or_404(db: Session, lecturer_id: int) -> User:
    lecturer = (
        db.query(User)
        .filter(
            User.id == lecturer_id,
            User.role == UserRole.LECTURER,
            User.email != PLACEHOLDER_USER_EMAIL,  # never a real, targetable account
        )
        .first()
    )
    if not lecturer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lecturer not found")
    return lecturer


# -------------------------
# CREATE LECTURER
# -------------------------
@router.post("/lecturers", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_lecturer(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    new_lecturer = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.LECTURER,
        is_active=True,
    )
    db.add(new_lecturer)
    db.commit()
    db.refresh(new_lecturer)
    return new_lecturer


# -------------------------
# LIST LECTURERS
# -------------------------
@router.get("/lecturers", response_model=list[UserOut])
def list_lecturers(include_inactive: bool = False, db: Session = Depends(get_db)):
    query = db.query(User).filter(
        User.role == UserRole.LECTURER,
        User.email != PLACEHOLDER_USER_EMAIL,
    )
    if not include_inactive:
        query = query.filter(User.is_active == True)  # noqa: E712
    return query.order_by(User.id).all()


# -------------------------
# DEACTIVATE LECTURER
# -------------------------
@router.patch("/lecturers/{lecturer_id}/deactivate", response_model=UserOut)
def deactivate_lecturer(lecturer_id: int, db: Session = Depends(get_db)):
    lecturer = _get_lecturer_or_404(db, lecturer_id)
    lecturer.is_active = False
    db.commit()
    db.refresh(lecturer)
    return lecturer


# -------------------------
# REACTIVATE LECTURER
# -------------------------
@router.patch("/lecturers/{lecturer_id}/reactivate", response_model=UserOut)
def reactivate_lecturer(lecturer_id: int, db: Session = Depends(get_db)):
    lecturer = _get_lecturer_or_404(db, lecturer_id)
    lecturer.is_active = True
    db.commit()
    db.refresh(lecturer)
    return lecturer


# -------------------------
# DELETE LECTURER
# -------------------------
@router.delete("/lecturers/{lecturer_id}")
def delete_lecturer(lecturer_id: int, db: Session = Depends(get_db)):
    lecturer = _get_lecturer_or_404(db, lecturer_id)

    try:
        # Unassigns any Units this lecturer owns and reassigns any authored
        # RuleVersions to the placeholder - same cleanup used for Admins.
        account_service.delete_user_with_cleanup(db, lecturer)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not delete lecturer")

    return {"detail": f"Lecturer {lecturer_id} deleted successfully"}