import os
import uuid
from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_SECRET_KEY", "local-test-secret-at-least-32-characters")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://journey:local-journey-db-password@db:5432/journey_test",
)
os.environ.setdefault("SEED_TEST_ACCOUNT", "false")

from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402

TRUNCATE_SQL = """
TRUNCATE TABLE
  agent_tool_runs, agent_confirmations, agent_runs,
  agent_threads,
  knowledge_chunks, knowledge_documents, knowledge_sources,
  audit_events, idempotency_keys, auth_sessions,
  weight_records, activity_records, food_records, goals,
  profiles, password_credentials, identities, users
CASCADE
"""


@pytest.fixture(autouse=True)
def isolated_database() -> Generator[None, None, None]:
    with engine.begin() as connection:
        connection.execute(text(TRUNCATE_SQL))
    yield
    with engine.begin() as connection:
        connection.execute(text(TRUNCATE_SQL))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def register_user(client: TestClient) -> Callable[..., dict]:
    def register(**overrides) -> dict:
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "email": f"user-{suffix}@example.com",
            "username": f"user_{suffix}",
            "password": "JourneyPass2026",
            "display_name": "Journey User",
            **overrides,
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201, response.text
        return {"payload": payload, "tokens": response.json()}

    return register


@pytest.fixture
def seeded_knowledge() -> None:
    from app.core.database import SessionLocal
    from app.knowledge.ingest import ingest_builtin_knowledge

    with SessionLocal() as db:
        assert ingest_builtin_knowledge(db) >= 4
