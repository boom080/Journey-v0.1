from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import engine
from app.models.agent import AgentRun
from app.models.food_record import FoodRecord


def auth(account: dict, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {account['tokens']['access_token']}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


def test_agent_multi_intent_candidates_require_confirmation(
    client: TestClient, register_user, seeded_knowledge
) -> None:
    account = register_user()
    result = client.post(
        "/api/v1/agent/runs",
        headers=auth(account),
        json={"message": "午餐吃了鸡肉饭 520 千卡，然后跑步 30 分钟 240 千卡"},
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert {item["intent"] for item in body["intents"]} == {"food", "activity"}
    assert {item["kind"] for item in body["candidates"]} == {"food", "activity"}
    assert body["fallback_used"] is True
    assert body["usage"]["provider"] == "mock"
    assert body["usage"]["estimated_cost_usd"] == 0

    with Session(engine) as db:
        assert db.query(FoodRecord).count() == 0
        run = db.scalar(select(AgentRun).where(AgentRun.id == body["run_id"]))
        assert run is not None
        assert run.input_hash != body.get("message")
        assert not hasattr(run, "raw_input")


def test_confirmation_is_owned_idempotent_and_writes_once(
    client: TestClient, register_user, seeded_knowledge
) -> None:
    owner = register_user()
    stranger = register_user()
    run = client.post(
        "/api/v1/agent/runs",
        headers=auth(owner),
        json={"message": "午餐吃了鸡肉饭 520 千卡"},
    ).json()
    candidate = run["candidates"][0]
    path = f"/api/v1/agent/confirmations/{candidate['candidate_id']}"
    request = {
        "confirmation_token": candidate["confirmation_token"],
        "kind": candidate["kind"],
        "payload": candidate["payload"],
    }

    denied = client.post(path, headers=auth(stranger, "agent-denied"), json=request)
    assert denied.status_code == 400

    first = client.post(path, headers=auth(owner, "agent-confirm-1"), json=request)
    replay = client.post(path, headers=auth(owner, "agent-confirm-1"), json=request)
    assert first.status_code == replay.status_code == 201
    assert first.json()["record"]["id"] == replay.json()["record"]["id"]
    assert replay.json()["replayed"] is True
    assert first.json()["record"]["source"] == "agent"
    assert first.json()["run_status"] == "completed"
    assert first.json()["resume_available"] is False

    second_key = client.post(path, headers=auth(owner, "agent-confirm-2"), json=request)
    assert second_key.status_code == 409
    assert second_key.json()["error"]["code"] == "confirmation_already_used"
    with Session(engine) as db:
        assert db.query(FoodRecord).count() == 1


def test_knowledge_citations_and_owner_only_trace(
    client: TestClient, register_user, seeded_knowledge
) -> None:
    owner = register_user()
    stranger = register_user()
    result = client.post(
        "/api/v1/agent/runs",
        headers=auth(owner),
        json={"message": "睡眠对训练恢复有什么影响？"},
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["answer"]
    assert body["citations"]
    assert all(item["chunk_id"] for item in body["citations"])

    trace = client.get(f"/api/v1/agent/runs/{body['run_id']}", headers=auth(owner))
    assert trace.status_code == 200
    trace_body = trace.json()
    assert trace_body["prompt_version"]
    assert trace_body["knowledge_version"]
    assert trace_body["tools"][0]["tool_name"] == "policy.guard"
    assert trace_body["tools"][0]["input_summary"] == {"step_count": 1}
    assert any(item["tool_name"] == "knowledge.answer" for item in trace_body["tools"])
    assert "睡眠对训练恢复有什么影响" not in trace.text
    denied = client.get(f"/api/v1/agent/runs/{body['run_id']}", headers=auth(stranger))
    assert denied.status_code == 404


def test_medical_question_uses_explainable_safety_fallback(
    client: TestClient, register_user, seeded_knowledge
) -> None:
    account = register_user()
    result = client.post(
        "/api/v1/agent/runs",
        headers=auth(account),
        json={"message": "胸痛应该吃什么药？"},
    )
    assert result.status_code == 200
    body = result.json()
    assert "不提供诊断或治疗建议" in body["answer"]
    assert body["citations"]
    assert body["candidates"] == []


def test_unknown_input_requests_clarification(client: TestClient, register_user) -> None:
    account = register_user()
    result = client.post(
        "/api/v1/agent/runs",
        headers=auth(account),
        json={"message": "帮我处理一下"},
    )
    assert result.status_code == 200
    assert result.json()["status"] == "clarification_required"


def test_recommendation_and_weekly_workflow_nodes_are_traced(
    client: TestClient, register_user, seeded_knowledge
) -> None:
    account = register_user()
    for message, prefix in (
        ("根据今天记录给我建议", "recommendation"),
        ("请生成本周总结", "weekly_summary"),
    ):
        result = client.post("/api/v1/agent/runs", headers=auth(account), json={"message": message})
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["answer"]
        assert body["citations"]
        trace = client.get(f"/api/v1/agent/runs/{body['run_id']}", headers=auth(account))
        names = {item["tool_name"] for item in trace.json()["tools"]}
        assert {f"{prefix}.context", f"{prefix}.retrieve", f"{prefix}.generate"} <= names


def test_partial_multi_intent_failure_keeps_safe_candidate(
    client: TestClient, register_user, seeded_knowledge
) -> None:
    account = register_user()
    result = client.post(
        "/api/v1/agent/runs",
        headers=auth(account),
        json={"message": "体重 999，然后午餐吃苹果 80 千卡"},
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "waiting_for_user"
    assert body["verification"]["passed"] is False
    assert [item["kind"] for item in body["candidates"]] == ["food"]
    assert any(event["type"] == "error" for event in body["events"])
