import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from app.core.database import SessionLocal, engine
from app.core.settings import get_settings
from app.models.agent import AgentConfirmation, AgentRun, AgentThread, AgentToolRun
from app.models.agent_privacy import AgentConsent
from app.models.auth_session import AuthSession
from app.models.food_record import FoodRecord
from app.models.idempotency import IdempotencyKey
from app.services.agent_privacy import policy_version
from tests.test_agent_privacy import create_run, headers


def test_isolated_restore_scrub_revokes_old_tokens_without_changing_saved_health(
    client, register_user
):
    # This test operates exclusively on the existing disposable test database.
    assert engine.url.database == "journey_test"
    account = register_user()
    uid = uuid.UUID(account["tokens"]["user"]["id"])
    run = create_run(client, account)
    candidate = run["candidates"][0]
    confirmed = client.post(
        f"/api/v1/agent/confirmations/{candidate['candidate_id']}",
        headers={**headers(account), "Idempotency-Key": "restore-confirmation"},
        json={
            "kind": candidate["kind"],
            "confirmation_token": candidate["confirmation_token"],
            "payload": candidate["payload"],
        },
    )
    assert confirmed.status_code == 201
    with SessionLocal() as db:
        db.add(
            AgentConsent(
                user_id=uid,
                policy_version=policy_version(get_settings()),
                granted_at=datetime.now(UTC),
            )
        )
        db.commit()
        preserved = [(row.id, row.name, row.energy_kcal) for row in db.scalars(select(FoodRecord))]
        assert preserved

    sql_path = Path(__file__).resolve().parents[2] / "infra/privacy/scrub-restored-agent.sql"
    with engine.connect().execution_options(
        isolation_level="AUTOCOMMIT", no_parameters=True
    ) as connection:
        connection.exec_driver_sql(sql_path.read_text())
    with SessionLocal() as db:
        for model in (
            AgentRun,
            AgentToolRun,
            AgentConfirmation,
            AgentThread,
            AgentConsent,
            IdempotencyKey,
        ):
            assert db.scalar(select(func.count()).select_from(model)) == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuthSession)
                .where(AuthSession.revoked_at.is_(None))
            )
            == 0
        )
        assert [
            (row.id, row.name, row.energy_kcal) for row in db.scalars(select(FoodRecord))
        ] == preserved
    # An old access token must not survive restoring an old session row.
    assert client.get("/api/v1/agent/privacy", headers=headers(account)).status_code == 401
    login = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": account["payload"]["email"],
            "password": account["payload"]["password"],
        },
    )
    assert login.status_code == 200
    fresh = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert not client.get("/api/v1/agent/privacy", headers=fresh).json()["consent_granted"]
    assert client.get(f"/api/v1/agent/runs/{run['run_id']}", headers=fresh).status_code == 404
