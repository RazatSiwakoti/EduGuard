"""HTTP smoke tests for the lecturer alerts API."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.routes.alerts import router
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.base import Base
from app.models.enums import UserRole
from app.models.user import User
from app.services import alert_service
from app.services import email_backend


def test_alert_api_is_reachable_and_tenant_scoped(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    lecturer = User(email="lecturer@example.com", full_name="Lecturer", role=UserRole.LECTURER, hashed_password="x", is_active=True)
    db.add(lecturer)
    db.commit()
    api = FastAPI()
    api.include_router(router)
    api.dependency_overrides[get_db] = lambda: db
    api.dependency_overrides[get_current_user] = lambda: lecturer
    monkeypatch.setattr(email_backend, "get_email_backend", lambda: email_backend.ConsoleBackend())
    monkeypatch.setattr(alert_service, "get_email_backend", email_backend.get_email_backend)
    client = TestClient(api)
    response = client.get("/lecturer/alerts/summary")
    assert response.status_code == 200
    assert response.json()["unit_count"] == 0
    assert client.get("/lecturer/alerts/placeholders").status_code == 200
