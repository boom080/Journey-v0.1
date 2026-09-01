import base64
import io
import json
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select, update

from app.agent.model_router import ModelAdapter, ModelRouter, _safe_error_code
from app.api.errors import APIError
from app.core.database import SessionLocal
from app.core.privacy import PrivacyLogFilter, prepare_model_prompt
from app.core.settings import get_settings
from app.media.food_image import MockFoodImageAnalyzer, analyze_food_image
from app.models.agent import AgentConfirmation, AgentRun, AgentThread, AgentToolRun
from app.models.agent_privacy import AgentConsent, AgentDeletedCost
from app.models.food_record import FoodRecord
from app.models.idempotency import IdempotencyKey
from app.models.profile import Profile
from app.models.user import User
from app.schemas.agent import FoodParsed
from app.schemas.media import FoodImageAnalyzeRequest
from app.services.agent import run_agent
from app.services.agent_privacy import delete_agent_data, purge_expired_agent_data
from tests.privacy_helpers import synthetic_review

PRIVACY = "/api/v1/agent/privacy"


class RecordingAdapter(ModelAdapter):
    provider = "deepseek"
    calls = []
    constructions = 0

    def __init__(self, settings=None):
        type(self).constructions += 1

    def invoke_structured(self, **kwargs):
        type(self).calls.append({"system": kwargs["system_prompt"], "user": kwargs["user_prompt"]})
        return kwargs["fallback_factory"](), 10, 10


@pytest.fixture
def external(monkeypatch):
    for key, value in {
        "AGENT_PROVIDER": "deepseek",
        "DEEPSEEK_API_KEY": "synthetic-key-no-network",
        "DEEPSEEK_DEFAULT_MODEL": "deepseek-v4-flash",
        "AGENT_DAILY_BUDGET_USD": "1",
        "AGENT_EXTERNAL_ENABLED": "true",
        "AGENT_PROVIDER_POLICY_URL": "https://example.invalid/privacy",
        "AGENT_PROVIDER_RETENTION_NOTICE": (
            "Synthetic test-only provider retention and deletion policy. No real requests."
        ),
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    monkeypatch.setenv("AGENT_PROVIDER_REVIEW_JSON", synthetic_review(get_settings()))
    get_settings.cache_clear()
    RecordingAdapter.calls = []
    RecordingAdapter.constructions = 0
    monkeypatch.setattr("app.agent.model_router.LangChainLiteLLMAdapter", RecordingAdapter)
    yield
    get_settings.cache_clear()


def headers(account):
    return {"Authorization": f"Bearer {account['tokens']['access_token']}"}


def grant(client, account):
    state = client.get(PRIVACY, headers=headers(account)).json()
    response = client.put(
        f"{PRIVACY}/consent",
        headers=headers(account),
        json={"granted": True, "policy_version": state["policy_version"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["consent_granted"]
    return state


def create_run(client, account, message="午餐吃了鸡肉 200 kcal"):
    response = client.post(
        "/api/v1/agent/runs", headers=headers(account), json={"message": message}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_unconsented_api_and_direct_router_never_construct_or_call_provider(
    external, client, register_user
):
    account = register_user()
    state = client.get(PRIVACY, headers=headers(account)).json()
    assert state["external"] and state["enabled"] and not state["consent_granted"]
    response = client.post(
        "/api/v1/agent/runs", headers=headers(account), json={"message": "午餐吃了鸡肉"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "consent_required"
    with SessionLocal() as db:
        router = ModelRouter(db)
        assert router.adapter is None
        with pytest.raises(APIError, match="同意"):
            router.generate(
                "food_text_parse",
                FoodParsed,
                system_prompt="test",
                user_prompt="test",
                fallback_factory=lambda: FoodParsed(meal_type="other", name="test", energy_kcal=1),
            )
        assert db.scalar(select(func.count()).select_from(AgentRun)) == 0
    assert RecordingAdapter.constructions == 0
    assert RecordingAdapter.calls == []


def test_consent_is_versioned_account_scoped_revocable_and_resume_is_gated(
    external, client, register_user, monkeypatch
):
    first, second = register_user(), register_user()
    stale = client.put(
        f"{PRIVACY}/consent",
        headers=headers(first),
        json={"granted": True, "policy_version": "old"},
    )
    assert stale.status_code == 409
    state = grant(client, first)
    run = create_run(client, first)
    assert RecordingAdapter.calls
    count = len(RecordingAdapter.calls)
    assert (
        client.post(
            "/api/v1/agent/runs", headers=headers(second), json={"message": "跑步30分钟"}
        ).status_code
        == 403
    )
    # Caller-supplied identity/consent fields cannot authorize a different account.
    assert (
        client.put(
            f"{PRIVACY}/consent",
            headers=headers(second),
            json={
                "granted": True,
                "policy_version": state["policy_version"],
                "user_id": first["tokens"]["user"]["id"],
            },
        ).status_code
        == 422
    )
    monkeypatch.setenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-v4-pro")
    get_settings.cache_clear()
    monkeypatch.setenv("AGENT_PROVIDER_REVIEW_JSON", synthetic_review(get_settings()))
    get_settings.cache_clear()
    changed = client.post(
        "/api/v1/agent/runs", headers=headers(first), json={"message": "午餐吃了鸡肉"}
    )
    assert changed.json()["error"]["code"] == "consent_outdated"
    revoke = client.put(
        f"{PRIVACY}/consent",
        headers=headers(first),
        json={"granted": False, "policy_version": "old"},
    )
    assert revoke.status_code == 200 and not revoke.json()["consent_granted"]
    assert (
        client.post(
            f"/api/v1/agent/runs/{run['run_id']}/resume", headers=headers(first)
        ).status_code
        == 403
    )
    assert len(RecordingAdapter.calls) == count


def test_operator_kill_switch_and_invalid_policy_fail_closed(
    external, client, register_user, monkeypatch
):
    account = register_user()
    grant(client, account)
    monkeypatch.setenv("AGENT_EXTERNAL_ENABLED", "false")
    get_settings.cache_clear()
    result = client.post(
        "/api/v1/agent/runs", headers=headers(account), json={"message": "午餐吃了鸡肉"}
    )
    assert result.status_code == 503
    assert RecordingAdapter.calls == []
    monkeypatch.setenv("AGENT_EXTERNAL_ENABLED", "true")
    monkeypatch.setenv("AGENT_PROVIDER_POLICY_URL", "http://unsafe.invalid/policy")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="HTTPS"):
        get_settings()


def test_outbound_prompt_and_persisted_trace_exclude_identifiers(
    external, client, register_user, seeded_knowledge
):
    account = register_user(display_name="PrivateJourneyName")
    uid = uuid.UUID(account["tokens"]["user"]["id"])
    with SessionLocal() as db:
        profile = db.scalar(select(Profile).where(Profile.user_id == uid))
        profile.birth_date = datetime(1991, 2, 3).date()
        db.commit()
    grant(client, account)
    secrets = [
        account["payload"]["email"],
        "PrivateJourneyName",
        "13812345678",
        "sk-sensitivefixture123",
        "privatepass123",
        "1991-02-03",
    ]
    run = create_run(
        client,
        account,
        f"{secrets[0]} PrivateJourneyName 13812345678 "
        "api_key=sk-sensitivefixture123 password=privatepass123 1991-02-03；给我建议",
    )
    outbound = json.dumps(RecordingAdapter.calls, ensure_ascii=False)
    for secret in [*secrets, str(uid)]:
        assert secret not in outbound
    assert "birth_date" not in outbound and "user_id" not in outbound
    trace = client.get(f"/api/v1/agent/runs/{run['run_id']}", headers=headers(account))
    assert trace.status_code == 200
    for secret in secrets:
        assert secret not in trace.text
    with SessionLocal() as db:
        stored = db.get(AgentRun, uuid.UUID(run["run_id"]))
        stored.plan = {**stored.plan, "goal": "raw-health-diary", "email": secrets[0]}
        db.add(
            AgentToolRun(
                run_id=stored.id,
                tool_name="test",
                status="completed",
                input_summary={
                    "message": "raw-health-diary",
                    "unknown": "raw-health-diary",
                    "input_length": 12,
                },
                output_summary={"citation_count": 1, "access_token": secrets[3]},
            )
        )
        db.commit()
        payload = json.dumps(
            [
                stored.plan,
                *[tool.input_summary for tool in stored.tool_runs],
                *[tool.output_summary for tool in stored.tool_runs],
            ]
        )
        assert "raw-health-diary" not in payload
        assert secrets[0] not in payload and secrets[3] not in payload


def test_minimal_context_is_allowlisted_and_memory_does_not_send_run_ids():
    payload = {
        "context": {
            "profile": {"birth_date": "1990-01-01"},
            "user_id": "private-id",
            "goal": {"kind": "maintain", "id": "private-id"},
            "today": {"intake_kcal": 500, "active_goal": {"user_id": "private-id"}},
            "recent_totals": {"food_count": 2, "notes": "private-notes"},
        },
        "chunks": [{"chunk_id": "chunk-1", "text": "public", "private_key": "private-notes"}],
    }
    result = prepare_model_prompt("recommendation", json.dumps(payload))
    assert (
        "private-id" not in result and "birth_date" not in result and "private-notes" not in result
    )
    assert json.loads(result)["context"]["today"]["intake_kcal"] == 500
    memory = prepare_model_prompt(
        "intent_classification",
        json.dumps(
            {
                "message": "继续",
                "recent_thread_memory": [
                    {"run_id": "private-id", "intents": ["food"], "notes": "private-notes"}
                ],
            }
        ),
    )
    assert "private-id" not in memory and "private-notes" not in memory


def test_delete_contract_removes_agent_graph_and_replays_but_preserves_records(
    external, client, register_user
):
    first, second = register_user(), register_user()
    grant(client, first)
    grant(client, second)
    run = create_run(client, first)
    other = create_run(client, second)
    candidate = run["candidates"][0]
    confirmed = client.post(
        f"/api/v1/agent/confirmations/{candidate['candidate_id']}",
        headers={**headers(first), "Idempotency-Key": "privacy-confirm"},
        json={
            "kind": candidate["kind"],
            "confirmation_token": candidate["confirmation_token"],
            "payload": candidate["payload"],
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    assert client.delete(f"{PRIVACY}/data").status_code == 401
    deleted = client.delete(f"{PRIVACY}/data", headers=headers(first))
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted_runs"] == 1
    assert deleted.json()["deleted_threads"] == 1
    assert deleted.json()["consent_revoked"] is True
    assert deleted.json()["provider_data_deleted"] is False
    uid = uuid.UUID(first["tokens"]["user"]["id"])
    with SessionLocal() as db:
        for model in (AgentRun, AgentThread, AgentConfirmation, AgentConsent):
            assert (
                db.scalar(select(func.count()).select_from(model).where(model.user_id == uid)) == 0
            )
        assert (
            db.scalar(
                select(func.count())
                .select_from(AgentToolRun)
                .where(AgentToolRun.run_id == uuid.UUID(run["run_id"]))
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(IdempotencyKey)
                .where(IdempotencyKey.user_id == uid)
            )
            == 0
        )
        assert (
            db.scalar(select(func.count()).select_from(FoodRecord).where(FoodRecord.user_id == uid))
            == 1
        )
    assert (
        client.get(f"/api/v1/agent/runs/{run['run_id']}", headers=headers(first)).status_code == 404
    )
    assert (
        client.get(f"/api/v1/agent/runs/{other['run_id']}", headers=headers(second)).status_code
        == 200
    )
    assert client.delete(f"{PRIVACY}/data", headers=headers(first)).json()["deleted_runs"] == 0
    assert (
        client.post(
            "/api/v1/agent/runs", headers=headers(first), json={"message": "跑步30分钟"}
        ).status_code
        == 403
    )


def test_retention_sweep_is_not_traffic_dependent(client, register_user):
    account = register_user()
    old = create_run(client, account)
    new = create_run(client, account)
    cutoff = datetime.now(UTC) - timedelta(days=8)
    with SessionLocal() as db:
        db.execute(
            update(AgentRun)
            .where(AgentRun.id == uuid.UUID(old["run_id"]))
            .values(created_at=cutoff)
        )
        db.execute(
            update(AgentThread)
            .where(AgentThread.id == uuid.UUID(old["thread_id"]))
            .values(updated_at=cutoff)
        )
        db.commit()
    purge_expired_agent_data()
    with SessionLocal() as db:
        assert db.get(AgentRun, uuid.UUID(old["run_id"])) is None
        assert db.get(AgentThread, uuid.UUID(old["thread_id"])) is None
        assert db.get(AgentRun, uuid.UUID(new["run_id"])) is not None
        assert (
            db.scalar(
                select(func.count())
                .select_from(AgentConfirmation)
                .where(AgentConfirmation.run_id == uuid.UUID(old["run_id"]))
            )
            == 0
        )


def test_delete_cannot_reset_model_budget(external, client, register_user):
    account = register_user()
    uid = uuid.UUID(account["tokens"]["user"]["id"])
    grant(client, account)
    run = create_run(client, account)
    with SessionLocal() as db:
        db.execute(
            update(AgentRun)
            .where(AgentRun.id == uuid.UUID(run["run_id"]))
            .values(estimated_cost_usd=Decimal("1"))
        )
        db.commit()
    assert client.delete(f"{PRIVACY}/data", headers=headers(account)).status_code == 200
    grant(client, account)
    count = len(RecordingAdapter.calls)
    with SessionLocal() as db:
        assert db.scalar(select(AgentDeletedCost.cost_usd)) == Decimal("1")
        result = ModelRouter(db, user_id=uid).generate(
            "food_text_parse",
            FoodParsed,
            system_prompt="test",
            user_prompt="午餐",
            fallback_factory=lambda: FoodParsed(meal_type="other", name="test", energy_kcal=1),
        )
        assert result.error_code == "agent_daily_budget_exceeded"
    assert len(RecordingAdapter.calls) == count


@pytest.mark.parametrize("run_kind", ["text", "mock_image"])
def test_delete_waits_for_inflight_run_and_prevents_resurrection(
    external, client, register_user, run_kind
):
    account = register_user()
    uid = uuid.UUID(account["tokens"]["user"]["id"])
    grant(client, account)
    entered, release, deleting = threading.Event(), threading.Event(), threading.Event()

    class BlockingAdapter(RecordingAdapter):
        def invoke_structured(self, **kwargs):
            entered.set()
            assert release.wait(5)
            return super().invoke_structured(**kwargs)

    class BlockingImageAnalyzer(MockFoodImageAnalyzer):
        def analyze(self, **kwargs):
            entered.set()
            assert release.wait(5)
            return super().analyze(**kwargs)

    def execute():
        with SessionLocal() as db:
            if run_kind == "mock_image":
                return analyze_food_image(
                    db,
                    db.get(User, uid),
                    request_id="privacy-image-concurrency",
                    analyzer=BlockingImageAnalyzer(),
                    payload=FoodImageAnalyzeRequest(
                        image_base64=base64.b64encode(b"\xff\xd8\xffsynthetic-image").decode(),
                        media_type="image/jpeg",
                        width=10,
                        height=10,
                        confirm_upload=True,
                    ),
                )
            return run_agent(
                db,
                db.get(User, uid),
                message="午餐吃了鸡肉 200 kcal",
                request_id="privacy-concurrency",
                model_router=ModelRouter(db, adapter=BlockingAdapter()),
            )

    def erase():
        with SessionLocal() as db:
            deleting.set()
            return delete_agent_data(db, uid)

    with ThreadPoolExecutor(max_workers=2) as pool:
        run_future = pool.submit(execute)
        try:
            assert entered.wait(5)
            deletion_future = pool.submit(erase)
            assert deleting.wait(5)
            with pytest.raises(FutureTimeout):
                deletion_future.result(timeout=0.1)
        finally:
            release.set()
        run_future.result(timeout=5)
        assert deletion_future.result(timeout=5).deleted_runs == 1
    with SessionLocal() as db:
        assert (
            db.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.user_id == uid))
            == 0
        )
    assert not client.get(PRIVACY, headers=headers(account)).json()["consent_granted"]


def test_runtime_error_and_exception_logs_do_not_echo_payloads():
    secret = "patient@example.com 13812345678 sk-privatefixture123"
    assert _safe_error_code(RuntimeError(secret)) == "model_unavailable"
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(PrivacyLogFilter())
    logger = logging.getLogger("privacy-test-isolated")
    logger.handlers = [handler]
    logger.propagate = False
    try:
        raise RuntimeError("raw-health-diary " + secret)
    except RuntimeError:
        logger.error("provider failure %s", secret, exc_info=True)
    text = stream.getvalue()
    for value in ("raw-health-diary", "patient@example.com", "13812345678", "sk-privatefixture123"):
        assert value not in text


def test_provider_exception_is_not_recorded_in_otel_or_api_error(
    external, client, register_user, monkeypatch
):
    account = register_user()
    grant(client, account)
    attrs, span_options = {}, {}

    class Span:
        def set_attribute(self, key, value):
            attrs[key] = value

    class Tracer:
        @contextmanager
        def start_as_current_span(self, name, **options):
            span_options.update(options)
            yield Span()

    class LeakyAdapter(RecordingAdapter):
        def invoke_structured(self, **kwargs):
            raise RuntimeError("raw-health-diary patient@example.com sk-privatefixture123")

    monkeypatch.setattr("app.agent.model_router.tracer", Tracer())
    monkeypatch.setattr("app.agent.model_router.LangChainLiteLLMAdapter", LeakyAdapter)
    run = create_run(client, account)
    assert span_options == {"record_exception": False, "set_status_on_exception": False}
    assert attrs["journey.agent.error_code"] == "model_unavailable"
    for secret in ("raw-health-diary", "patient@example.com", "sk-privatefixture123"):
        assert secret not in json.dumps(attrs)
        assert secret not in json.dumps(run)


def test_each_retry_rechecks_consent(external, client, register_user):
    account = register_user()
    grant(client, account)
    uid = uuid.UUID(account["tokens"]["user"]["id"])
    with SessionLocal() as db:
        calls = []

        class RevokingAdapter(RecordingAdapter):
            def invoke_structured(self, **kwargs):
                calls.append(True)
                consent = db.get(AgentConsent, uid)
                consent.granted_at = None
                db.flush()
                raise TimeoutError("synthetic timeout")

        router = ModelRouter(db, user_id=uid, adapter=RevokingAdapter())
        with pytest.raises(APIError) as error:
            router.generate(
                "food_text_parse",
                FoodParsed,
                system_prompt="test",
                user_prompt="午餐",
                fallback_factory=lambda: FoodParsed(meal_type="other", name="test", energy_kcal=1),
            )
        assert error.value.code == "consent_required"
        assert len(calls) == 1


@pytest.mark.parametrize("retention", ["0", "31"])
def test_retention_configuration_is_bounded(monkeypatch, retention):
    monkeypatch.setenv("AGENT_DATA_RETENTION_DAYS", retention)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="AGENT_DATA_RETENTION_DAYS"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_real_sdk_telemetry_is_disabled():
    import litellm

    assert litellm.turn_off_message_logging is True
    assert litellm.suppress_debug_info is True
    assert litellm.callbacks == []
    assert not logging.getLogger("LiteLLM").propagate


def test_server_exception_and_access_logging_remain_safe_and_formattable():
    from uvicorn.logging import AccessFormatter

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        assert any(isinstance(item, PrivacyLogFilter) for item in logging.getLogger(name).filters)
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "test",
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("192.0.2.1", "POST", "/api/v1/agent/runs?text=private-health-diary", "1.1", 200),
        None,
    )
    PrivacyLogFilter().filter(record)
    rendered = AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s').format(
        record
    )
    assert "POST /api/v1/agent/runs HTTP/1.1" in rendered
    assert "private-health-diary" not in rendered
    assert "192.0.2.1" not in rendered


@pytest.mark.parametrize("review", ["", "{}", "not-json"])
def test_missing_provider_review_blocks_even_consented_accounts(
    external, client, register_user, monkeypatch, review
):
    account = register_user()
    grant(client, account)
    monkeypatch.setenv("AGENT_PROVIDER_REVIEW_JSON", review)
    get_settings.cache_clear()
    assert not client.get(PRIVACY, headers=headers(account)).json()["enabled"]
    response = client.post(
        "/api/v1/agent/runs", headers=headers(account), json={"message": "午餐吃了鸡肉"}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "agent_provider_review_required"
    assert RecordingAdapter.constructions == 0
    assert RecordingAdapter.calls == []
