"""
Seeds test Admin and Lecturer accounts for local development ONLY.

Refuses to run unless ENVIRONMENT=development, so a test account can never accidentally land in a production database. Kept separate from
seed_super_admin.py on purpose - real seed data and test fixtures should never share a file.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import SessionLocal
from app.models.user import User
from app.models.enums import UserRole
from app.core.security import hash_password

TEST_ACCOUNTS = [
    {
        "email": "test.admin@eduguard.com",
        "full_name": "Test Admin",
        "password": "TestAdmin123",
        "role": UserRole.ADMIN,
    },
    {
        "email": "test.lecturer@eduguard.com",
        "full_name": "Test Lecturer",
        "password": "TestLecturer123",
        "role": UserRole.LECTURER,
    },
]


def seed_dev_users() -> None:
    if settings.ENVIRONMENT != "development":
        print("Refusing to run: ENVIRONMENT is not 'development'.")
        return

    db = SessionLocal()

    try:
        for account in TEST_ACCOUNTS:
            existing = db.query(User).filter(User.email == account["email"]).first()
            if existing:
                print(f"Already exists, skipping: {account['email']}")
                continue

            user = User(
                email=account["email"],
                full_name=account["full_name"],
                hashed_password=hash_password(account["password"]),
                role=account["role"],
                is_active=True,
            )
            db.add(user)
            print(f"Created {account['role'].value}: {account['email']} / {account['password']}")

        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    seed_dev_users()

    