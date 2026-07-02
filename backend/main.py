"""
EduGuard FastAPI Application Entry Point.

Table creation is now handled entirely by Alembic migrations —
create_all() and the model imports it required have been removed
from here on purpose, so there's exactly one source of truth for
schema changes (alembic/versions/), not two.
"""

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)


@app.get("/")
def root():
    """Basic liveness check — confirms the API process itself is running."""
    return {
        "message": "EduGuard API running",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Confirms the API can actually reach PostgreSQL, not just that
    FastAPI booted. Runs a trivial SELECT 1 against the live connection.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "database": db_status
    }