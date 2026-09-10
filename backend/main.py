"""
EduGuard FastAPI Application Entry Point.

Table creation is now handled entirely by Alembic migrations — create_all() and the model imports it required have been removed
from here on purpose, so there's exactly one source of truth for schema changes (alembic/versions/), not two.
"""

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.api.routes import risk
from app.api.routes.auth import router as auth_router
from app.api.routes.super_admin import router as super_admin_router
from app.api.routes.lecturer import router as lecturer_router
from app.api.routes.admin import router as admin_router
from app.api.routes.units import router as units_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.criteria import router as criteria_router
from app.scheduler import start_scheduler, shutdown_scheduler
from fastapi.middleware.cors import CORSMiddleware
from app.models.verdict_review import VerdictReview
from app.api.routes.alerts import router as alerts_router
from app.api.routes.reports import router as reports_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.admin_criteria import router as admin_criteria_router
from app.api.routes.acknowledge import router as acknowledge_router
from app.api.routes.audit import router as audit_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.outcomes import router as outcomes_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.portal import router as portal_router
from app.api.routes.retention import router as retention_router
from app.api.routes.password_reset import router as password_reset_router



app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)
# Origins are deployment configuration, not application source.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#register routers
app.include_router(auth_router)
app.include_router(super_admin_router)
app.include_router(admin_router)
app.include_router(units_router)
app.include_router(ingestion_router)
app.include_router(criteria_router)
app.include_router(risk.router)
app.include_router(risk.unit_router)
app.include_router(lecturer_router)
app.include_router(alerts_router)
app.include_router(reports_router)
app.include_router(analysis_router)
app.include_router(admin_criteria_router)
app.include_router(acknowledge_router)
app.include_router(audit_router)
app.include_router(notifications_router)
app.include_router(outcomes_router)
app.include_router(evaluation_router)
app.include_router(portal_router)
app.include_router(retention_router)
app.include_router(password_reset_router)

@app.on_event("startup")
def _start_background_jobs() -> None:
    """
    Seeds the system email templates and starts the alert scheduler.

    RUN THIS API WITH A SINGLE WORKER. Under `uvicorn --workers 4`
    every worker executes this hook and starts its own scheduler, which
    without protection would mean four weekly sweeps and four copies of
    every student email. Both jobs take a PostgreSQL advisory lock so
    only one actually runs - but a single worker remains the correct
    way to deploy this, and the lock is the guard for the day someone
    forgets.
    """
    start_scheduler()


@app.on_event("shutdown")
def _stop_background_jobs() -> None:
    shutdown_scheduler()


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
