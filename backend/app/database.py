"""
Database connection and SQLAlchemy setup.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.base import Base


DATABASE_URL = settings.DATABASE_URL


# PostgreSQL connection
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# Database session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()