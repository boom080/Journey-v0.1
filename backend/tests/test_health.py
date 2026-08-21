from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import health
from app.main import app


def test_live_health_does_not_require_database_connection() -> None:
    response = TestClient(app).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "journey-api",
        "environment": "test",
    }
    assert response.headers["X-Request-ID"]


def test_ready_health_degrades_when_database_is_unavailable(monkeypatch) -> None:
    def unavailable_connection():
        raise SQLAlchemyError("database unavailable in test")

    monkeypatch.setattr(health.engine, "connect", unavailable_connection)

    response = TestClient(app).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
    assert response.json()["rag"] == "unavailable"
    assert response.json()["agent_mode"] == "MOCK"


def test_ready_health_exposes_non_secret_demo_runtime_mode(seeded_knowledge) -> None:
    response = TestClient(app).get("/health/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert response.json()["rag"] == "ok"
    assert response.json()["agent_mode"] == "MOCK"
    assert response.json()["agent_provider"] == "mock"
