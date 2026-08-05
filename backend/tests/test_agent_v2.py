import allure
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.execution_graph import run_execution_graph
from app.agent.planner import deterministic_plan
from app.agent.policy import validate_plan
from app.agent.tool_registry import ToolExecution
from app.core.database import engine
from app.core.settings import get_settings
from app.models.agent import AgentRun, AgentThread
from app.schemas.agent import AgentPlan, AgentPlanStep
from tests.allure_helpers import attach_json, sanitize_for_report

allure_epic = allure.epic("Journey Agent v2")


def auth(account: dict, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {account['tokens']['access_token']}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


@allure_epic
@allure.feature("Planner and policy")
def test_deterministic_planner_builds_bounded_dependency_plan() -> None:
    from app.agent.intent_router import deterministic_intent_plan

    message = "午餐吃苹果 80 千卡，然后跑步 30 分钟 180 千卡，然后根据今天记录给我建议"
    intent_plan = deterministic_intent_plan(message)
    plan = deterministic_plan(message, intent_plan)
    tools = [step.tool for step in plan.steps]

    assert len(plan.steps) <= 6
    assert tools == [
        "food.parse_candidate",
        "activity.parse_candidate",
        "context.load",
        "knowledge.retrieve",
        "recommendation.generate",
    ]
    assert plan.steps[-1].depends_on == ["step-3", "step-4"]
    assert validate_plan(plan).allowed is True
    attach_json("validated-plan", plan.model_dump(mode="json"))


@allure_epic
@allure.feature("Planner and policy")
def test_policy_rejects_confirmation_bypass_and_forward_dependency() -> None:
    plan = AgentPlan(
        goal="invalid",
        steps=[
            AgentPlanStep(
                id="step-1",
                tool="food.parse_candidate",
                reason="invalid confirmation policy",
                requires_confirmation=False,
                depends_on=["step-2"],
            ),
            AgentPlanStep(
                id="step-2",
                tool="profile.read",
                reason="read profile",
            ),
        ],
    )
    decision = validate_plan(plan)
    assert decision.allowed is False
    assert set(decision.violations) == {
        "invalid_or_forward_dependency",
        "confirmation_policy_mismatch",
    }


@allure_epic
@allure.feature("Execution recovery")
def test_execution_graph_replans_once_and_continues_independent_step() -> None:
    plan = AgentPlan(
        goal="recover",
        steps=[
            AgentPlanStep(id="step-1", tool="context.load", reason="load"),
            AgentPlanStep(
                id="step-2",
                tool="recommendation.generate",
                reason="generate",
                depends_on=["step-1"],
            ),
            AgentPlanStep(id="step-3", tool="profile.read", reason="independent"),
        ],
    )

    def execute(step: AgentPlanStep) -> ToolExecution:
        if step.id == "step-1":
            return ToolExecution(
                step.id, step.tool, "failed", "synthetic failure", 1, error_code="synthetic"
            )
        return ToolExecution(step.id, step.tool, "completed", "ok", 1)

    results, verification = run_execution_graph(plan, execute)
    assert [item.status for item in results] == ["failed", "skipped", "completed"]
    assert verification.replan_count == 1
    assert verification.failed_steps == 1
    assert verification.skipped_steps == 1
    assert verification.completed_steps == 1


def test_agent_v2_api_exposes_plan_thread_memory_and_owner_isolation(
    client, register_user, seeded_knowledge
) -> None:
    owner = register_user()
    stranger = register_user()
    message = "午餐吃苹果 80 千卡，然后跑步 30 分钟 180 千卡，然后根据今天记录给我建议"
    first = client.post("/api/v1/agent/runs", headers=auth(owner), json={"message": message})
    assert first.status_code == 200, first.text
    body = first.json()
    attach_json(
        "agent-v2-response",
        {
            "run_id": body["run_id"],
            "thread_id": body["thread_id"],
            "plan": body["plan"],
            "step_results": body["step_results"],
            "verification": body["verification"],
        },
    )
    assert body["thread_id"]
    assert body["plan"]["schema_version"] == "3"
    assert len(body["plan"]["steps"]) == 5
    assert body["verification"]["passed"] is True
    assert body["status"] == "waiting_for_user"
    assert body["verification"]["replan_count"] <= 2
    assert all(step["segment"] is None for step in body["plan"]["steps"])
    assert not any("write" in step["tool"] for step in body["plan"]["steps"])

    follow_up = client.post(
        "/api/v1/agent/runs",
        headers=auth(owner),
        json={"message": "那接下来怎么调整？", "thread_id": body["thread_id"]},
    )
    assert follow_up.status_code == 200, follow_up.text
    assert follow_up.json()["thread_id"] == body["thread_id"]
    assert [item["intent"] for item in follow_up.json()["intents"]] == ["recommendation"]

    denied = client.post(
        "/api/v1/agent/runs",
        headers=auth(stranger),
        json={"message": "继续", "thread_id": body["thread_id"]},
    )
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "agent_thread_not_found"

    with Session(engine) as db:
        thread = db.get(AgentThread, body["thread_id"])
        assert thread is not None
        serialized = str(thread.memory)
        assert message not in serialized
        assert "那接下来怎么调整" not in serialized
        run = db.scalar(select(AgentRun).where(AgentRun.id == body["run_id"]))
        assert run is not None
        assert message not in str(run.plan)
        assert all(step["segment"] is None for step in run.plan["steps"])


def test_confirmation_updates_structured_thread_memory(
    client, register_user, seeded_knowledge
) -> None:
    owner = register_user()
    run = client.post(
        "/api/v1/agent/runs",
        headers=auth(owner),
        json={"message": "午餐吃苹果 80 千卡"},
    ).json()
    candidate = run["candidates"][0]
    response = client.post(
        f"/api/v1/agent/confirmations/{candidate['candidate_id']}",
        headers=auth(owner, "agent-v2-confirm"),
        json={
            "confirmation_token": candidate["confirmation_token"],
            "kind": candidate["kind"],
            "payload": candidate["payload"],
        },
    )
    assert response.status_code == 201, response.text
    with Session(engine) as db:
        thread = db.get(AgentThread, run["thread_id"])
        assert thread is not None
        assert thread.memory[-1]["confirmed_kinds"] == ["food"]


def test_agent_v2_feature_flag_returns_legacy_contract(
    monkeypatch, client, register_user, seeded_knowledge
) -> None:
    owner = register_user()
    monkeypatch.setenv("AGENT_V2_ENABLED", "false")
    get_settings.cache_clear()
    try:
        response = client.post(
            "/api/v1/agent/runs",
            headers=auth(owner),
            json={"message": "午餐吃苹果 80 千卡"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["thread_id"] is None
        assert response.json()["plan"] is None
    finally:
        get_settings.cache_clear()


@allure_epic
@allure.feature("Test report privacy")
def test_allure_payload_sanitizer_redacts_secrets_and_raw_input() -> None:
    payload = {
        "authorization": "Bearer private",
        "api_key": "sk-private",
        "nested": {
            "password": "private",
            "message": "我的体重是 70kg",
            "segment": "午餐吃苹果",
            "safe": "completed",
        },
        "steps": [{"tool": "profile.read", "status": "completed"}],
    }

    sanitized = sanitize_for_report(payload)

    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["message"] == "[REDACTED]"
    assert sanitized["nested"]["segment"] == "[REDACTED]"
    assert sanitized["nested"]["safe"] == "completed"
    assert sanitized["steps"] == [{"tool": "profile.read", "status": "completed"}]
