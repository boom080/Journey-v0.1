import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.bootstrap_test_account import seed_test_account
from app.core.database import engine
from app.core.settings import get_settings
from app.main import app


def test_test_account_is_seeded_only_when_explicitly_enabled(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SEED_TEST_ACCOUNT", "true")
    monkeypatch.setenv("TEST_ACCOUNT_EMAIL", "demo@journey.local")
    monkeypatch.setenv("TEST_ACCOUNT_USERNAME", "journey_demo")
    monkeypatch.setenv("TEST_ACCOUNT_PASSWORD", "JourneyDemo2026")
    get_settings.cache_clear()
    try:
        with Session(engine) as db:
            assert seed_test_account(db) is True
            db.commit()
            assert seed_test_account(db) is False
    finally:
        get_settings.cache_clear()

    response = TestClient(app).post(
        "/api/v1/auth/login",
        json={"identifier": "journey_demo", "password": "JourneyDemo2026"},
    )
    assert response.status_code == 200


def test_openapi_contract_matches_snapshot() -> None:
    snapshot = Path(__file__).parent / "snapshots" / "openapi.json"
    assert json.loads(snapshot.read_text(encoding="utf-8")) == app.openapi()
    assert all("mini" not in path and "wechat" not in path for path in app.openapi()["paths"])
    assert all("ai" not in path and "rag" not in path for path in app.openapi()["paths"])
