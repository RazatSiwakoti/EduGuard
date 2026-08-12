"""
FastAPI Application Entry Point
Initializes the EduGuard backend with all routes and middleware
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import Base, engine
from app.api.routes import alerts, super_admin, students
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  LIFESPAN EVENTS
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan - runs on startup/shutdown
    """
    # Startup
    logger.info("🚀 Starting EduGuard Backend")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down EduGuard Backend")


# ─────────────────────────────────────────────
#  APP INITIALIZATION
# ─────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="Automated at-risk student detection and monitoring system",
    version="1.0.0",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────
#  MIDDLEWARE
# ─────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  API ROUTES
# ─────────────────────────────────────────────

# Health check
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


# Include routers
app.include_router(alerts.router)
app.include_router(super_admin.router)
app.include_router(students.router)


# ─────────────────────────────────────────────
#  ROOT ENDPOINT
# ─────────────────────────────────────────────

@app.get("/")
def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "description": "Automated at-risk student detection and monitoring system",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
