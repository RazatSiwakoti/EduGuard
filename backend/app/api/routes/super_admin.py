"""
Super Admin routes: manage Admin accounts only.

Strict silo, on purpose - a Super Admin manages Admin lifecycles and
nothing else. It has no ability here to touch Lecturers or Units; that
belongs entirely to Admin routes. Every query in this file explicitly
filters on role == ADMIN so a Lecturer or another Super Admin id can
never be affected by these endpoints, even by accident.
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
from app.services import account_service

router = APIRouter(
    prefix="/super-admin",
    tags=["Super Admin"],
    dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))],
)


def _get_admin_or_404(db: Session, admin_id: int) -> User:
    admin = db.query(User).filter(User.id == admin_id, User.role == UserRole.ADMIN).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    return admin


# -------------------------
# CREATE ADMIN
# -------------------------
@router.post("/admins", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_admin(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    new_admin = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin


# -------------------------
# LIST ADMINS
# -------------------------
@router.get("/admins", response_model=list[UserOut])
def list_admins(include_inactive: bool = False, db: Session = Depends(get_db)):
    query = db.query(User).filter(User.role == UserRole.ADMIN)
    if not include_inactive:
        query = query.filter(User.is_active == True)  # noqa: E712
    return query.order_by(User.id).all()


# -------------------------
# DEACTIVATE ADMIN
# -------------------------
@router.patch("/admins/{admin_id}/deactivate", response_model=UserOut)
def deactivate_admin(admin_id: int, db: Session = Depends(get_db)):
    admin = _get_admin_or_404(db, admin_id)
    admin.is_active = False
    db.commit()
    db.refresh(admin)
    return admin


# -------------------------
# REACTIVATE ADMIN
# -------------------------
@router.patch("/admins/{admin_id}/reactivate", response_model=UserOut)
def reactivate_admin(admin_id: int, db: Session = Depends(get_db)):
    admin = _get_admin_or_404(db, admin_id)
    admin.is_active = True
    db.commit()
    db.refresh(admin)
    return admin


# -------------------------
# DELETE ADMIN
# -------------------------
@router.delete("/admins/{admin_id}")
def delete_admin(admin_id: int, db: Session = Depends(get_db)):
    admin = _get_admin_or_404(db, admin_id)

    try:
        account_service.delete_user_with_cleanup(db, admin)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not delete admin")

    return {"detail": f"Admin {admin_id} deleted successfully"}