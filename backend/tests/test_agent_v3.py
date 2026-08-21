from datetime import UTC, datetime, timedelta

import allure
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.execution_graph import run_execution_graph_v3
from app.agent.model_router import ModelInvocation
from app.agent.tool_registry import ToolExecution
from app.core.database import engine
from app.core.settings import get_settings
from app.models.agent import AgentRun
from app.schemas.agent import AgentPlan, AgentPlanStep, AgentRecoveryDecision
from tests.allure_helpers import attach_json

allure_epic = allure.epic("Journey Agent v3")


def auth(account: dict, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {account['tokens']['access_token']}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


@allure_epic
@allure.feature("Human checkpoint")
def test_mixed_write_plan_pauses_confirms_and_resumes_with_fresh_data(
    client, register_user, seeded_knowledge
) -> None:
    account = register_user()
    response = client.post(
        "/api/v1/agent/runs",
        headers=auth(account),
        json={"message": "午餐吃苹果 80 千卡，然后跑步 30 分钟 180 千卡，再根据今天记录给建议"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "waiting_for_user"
    assert body["verification"]["decision"] == "wait_for_user"
    assert body["confirmation_progress"] == {
        "total": 2,
        "confirmed": 0,
        "pending": 2,
        "resume_available": False,
    }
    assert [item["tool"] for item in body["step_results"]] == [
        "food.parse_candidate",
        "activity.parse_candidate",
    ]
    assert not any(item["tool"] == "recommendation.generate" for item in body["step_results"])

    for index, candidate in enumerate(body["candidates"]):
        confirmed = client.post(
            f"/api/v1/agent/confirmations/{candidate['candidate_id']}",
            headers=auth(account, f"agent-v3-confirm-{index}"),
            json={
                "confirmation_token": candidate["confirmation_token"],
                "kind": candidate["kind"],
                "payload": candidate["payload"],
            },
        )
        assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["resume_available"] is True

    resumed = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/resume",
        headers=auth(account),
    )
    assert resumed.status_code == 200, resumed.text
    resumed_body = resumed.json()
    attach_json("agent-v3-resumed", resumed_body)
    assert resumed_body["status"] == "completed"
    assert resumed_body["answer"]
    assert "80.0" in resumed_body["answer"] or "80" in resumed_body["answer"]
    assert [item["tool"] for item in resumed_body["step_results"]] == [
        "context.load",
        "knowledge.retrieve",
        "recommendation.generate",
    ]

    duplicate = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/resume",
        headers=auth(account),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "agent_run_not_resumable"


@allure_epic
@allure.feature("Demo multi-agent collaboration")
def test_demo_compound_input_delegates_to_specialists_and_updates_journey(
    client, register_user, seeded_knowledge
) -> None:
    account = register_user()
    response = client.post(
        "/api/v1/agent/runs",
        headers=auth(account),
        json={"message": "今天中午吃了一份牛肉面，晚上跑了5公里，我这周减脂情况怎么样？"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "waiting_for_user"
    assert body["selected_agents"] == [
        "orchestrator",
        "record_agent",
        "journey_summary_agent",
        "health_knowledge_agent",
    ]
    assert [item["tool"] for item in body["plan"]["steps"]] == [
        "food.parse_candidate",
        "activity.parse_candidate",
        "context.load",
        "knowledge.retrieve",
        "weekly_summary.generate",
    ]
    assert [item["specialist"] for item in body["step_results"]] == [
        "record_agent",
        "record_agent",
    ]
    assert len(body["candidates"]) == 2

    for index, candidate in enumerate(body["candidates"]):
        confirmed = client.post(
            f"/api/v1/agent/confirmations/{candidate['candidate_id']}",
            headers=auth(account, f"demo-multi-agent-{index}"),
            json={
                "confirmation_token": candidate["confirmation_token"],
                "kind": candidate["kind"],
                "payload": candidate["payload"],
            },
        )
        assert confirmed.status_code == 201, confirmed.text

    resumed = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/resume",
        headers=auth(account),
    )
    assert resumed.status_code == 200, resumed.text
    resumed_body = resumed.json()
    assert resumed_body["status"] == "completed"
    assert resumed_body["answer"]
    assert [item["specialist"] for item in resumed_body["step_results"]] == [
        "journey_summary_agent",
        "health_knowledge_agent",
        "journey_summary_agent",
    ]
    home = client.get("/api/v1/home/today", headers=auth(account)).json()
    assert home["counts"]["food"] == 1
    assert home["counts"]["activity"] == 1


@allure_epic
@allure.feature("Checkpoint authorization")
def test_resume_rejects_pending_foreign_and_expired_checkpoints(
    client, register_user, seeded_knowledge
) -> None:
    owner = register_user()
    stranger = register_user()
    run = client.post(
        "/api/v1/agent/runs",
        headers=auth(owner),
        json={"message": "午餐吃苹果 80 千卡，然后根据今天记录给建议"},
    ).json()
    pending = client.post(f"/api/v1/agent/runs/{run['run_id']}/resume", headers=auth(owner))
    assert pending.status_code == 409
    assert pending.json()["error"]["code"] == "agent_confirmations_pending"
    denied = client.post(f"/api/v1/agent/runs/{run['run_id']}/resume", headers=auth(stranger))
    assert denied.status_code == 404

    with Session(engine) as db:
        stored = db.scalar(select(AgentRun).where(AgentRun.id == run["run_id"]))
        assert stored is not None
        stored.checkpoint_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    expired = client.post(f"/api/v1/agent/runs/{run['run_id']}/resume", headers=auth(owner))
    assert expired.status_code == 409
    assert expired.json()["error"]["code"] == "agent_checkpoint_expired"


@allure_epic
@allure.feature("Observe verify replan")
def test_execution_uses_allowlisted_recovery_and_stops_when_it_fails() -> None:
    plan = AgentPlan(
        goal="answer with recovery",
        steps=[
            AgentPlanStep(
                id="step-1",
                tool="knowledge.answer",
                reason="answer",
                segment="运动恢复",
            )
        ],
    )
    invocation = ModelInvocation(
        output=AgentRecoveryDecision(
            action="use_alternative",
            tool="knowledge.safe_summary",
            reason="safe fallback",
        ),
        provider="mock",
        model="journey-deterministic-v1",
        input_tokens=1,
        output_tokens=1,
        retries=0,
        latency_ms=1,
        estimated_cost_usd=0,
        fallback_used=True,
    )

    def replan(_observation):
        return invocation.output, invocation

    def recovered(step: AgentPlanStep) -> ToolExecution:
        if step.tool == "knowledge.answer":
            return ToolExecution(
                step.id,
                step.tool,
                "failed",
                "timeout",
                1,
                error_code="model_timeout",
            )
        return ToolExecution(step.id, step.tool, "completed", "safe summary", 1)

    outcome = run_execution_graph_v3(plan, recovered, replan)
    assert [item.tool for item in outcome.executions] == [
        "knowledge.answer",
        "knowledge.safe_summary",
    ]
    assert outcome.verification.decision == "fallback"
    assert outcome.verification.replan_count == 1
    assert outcome.verification.passed is True
    assert outcome.observations[0].allowed_alternatives == ["knowledge.safe_summary"]

    def failed(step: AgentPlanStep) -> ToolExecution:
        return ToolExecution(
            step.id,
            step.tool,
            "failed",
            "failed",
            1,
            error_code="model_timeout",
        )

    stopped = run_execution_graph_v3(plan, failed, replan)
    assert stopped.verification.decision == "stop"
    assert stopped.verification.replan_count == 1
    assert stopped.verification.passed is False


@allure_epic
@allure.feature("Checkpoint privacy")
def test_checkpoint_and_observations_do_not_store_raw_user_message(
    client, register_user, seeded_knowledge
) -> None:
    account = register_user()
    secret_phrase = "午餐吃私密苹果 80 千卡，然后根据今天记录给建议"
    run = client.post(
        "/api/v1/agent/runs",
        headers=auth(account),
        json={"message": secret_phrase},
    ).json()
    with Session(engine) as db:
        stored = db.scalar(select(AgentRun).where(AgentRun.id == run["run_id"]))
        assert stored is not None
        serialized = str(
            {
                "plan": stored.plan,
                "checkpoint": stored.checkpoint,
                "observations": stored.observations,
            }
        )
        assert secret_phrase not in serialized
        assert "私密苹果" not in serialized


@allure_epic
@allure.feature("Rollback flag")
def test_agent_v3_flag_can_roll_back_to_v2(
    monkeypatch, client, register_user, seeded_knowledge
) -> None:
    account = register_user()
    monkeypatch.setenv("AGENT_V3_ENABLED", "false")
    get_settings.cache_clear()
    try:
        response = client.post(
            "/api/v1/agent/runs",
            headers=auth(account),
            json={"message": "午餐吃苹果 80 千卡，然后根据今天记录给建议"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "completed"
        assert any(item["tool"] == "recommendation.generate" for item in body["step_results"])
    finally:
        get_settings.cache_clear()
