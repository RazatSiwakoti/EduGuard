""" 
Seeds the single, real Super Admin account.
Idempotent: checks whether a Super Admin already exists before inserting, so re-running this script is harmless.
"""


import sys
from pathlib import Path
from getpass import getpass

# Makes "from app..." imports work regardless of the working
# directory this script is launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.user import User
from app.models.enums import UserRole
from app.core.security import hash_password

def seed_super_admin() -> None:
    db = SessionLocal()

    try:
        existing = db.query(User).filter(
            User.role == UserRole.SUPER_ADMIN
        ).first()

        if existing:
             print(f"A Super Admin already exists: {existing.email}. Nothing to do.")
             return
        
        print("No Super Admin found. Creating one now.")
        email = input("Super Admin email: ").strip()
        full_name = input("Super Admin full name: ").strip()
        # getpass hides input so 
        #the password never echoes to the terminal or ends up in shell history.
        password = getpass("Super Admin password: ")
        

        super_admin = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )

        db.add(super_admin)
        db.commit()

        print(f"Super Admin created: {email}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_super_admin()