"""
EduGuard FastAPI Application Entry Point.
"""

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.models import User
from app.models.base import Base

# NOTE: Base.metadata.create_all() intentionally removed here.
# Once Alembic is introduced in Phase 1, migrations — not app startup —
# should own table creation, to avoid schema drift between the two.

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {
        "message": "EduGuard API running",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    # Actually exercises the DB connection, not just a static response —
    # this is what proves the .env path fix and DATABASE_URL are correct
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "database": db_status
    }

