import json
import os
import re
import time
import uuid

import allure
import requests

BASE_URL = os.getenv("BLACKBOX_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("BLACKBOX_TIMEOUT_SECONDS", "15"))


def request(session: requests.Session, method: str, path: str, **kwargs) -> requests.Response:
    started = time.perf_counter()
    response = session.request(
        method,
        f"{BASE_URL}{path}",
        timeout=TIMEOUT_SECONDS,
        **kwargs,
    )
    allure.attach(
        json.dumps(
            {
                "method": method,
                "path": path,
                "status": response.status_code,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            },
            sort_keys=True,
        ),
        name=f"{method}-{path.replace('/', '-')}",
        attachment_type=allure.attachment_type.JSON,
    )
    return response


@allure.epic("Journey network black-box")
@allure.feature("Agent v3 checkpoint journey")
def test_agent_checkpoint_confirm_resume_over_real_http() -> None:
    session = requests.Session()
    health = request(session, "GET", "/health/ready")
    assert health.status_code == 200, health.text

    suffix = uuid.uuid4().hex[:10]
    registered = request(
        session,
        "POST",
        "/api/v1/auth/register",
        json={
            "email": f"blackbox-{suffix}@example.com",
            "username": f"blackbox_{suffix}",
            "password": "JourneyBlackbox2026",
            "display_name": "Blackbox User",
        },
    )
    assert registered.status_code == 201, registered.text
    token = registered.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})

    created = request(
        session,
        "POST",
        "/api/v1/agent/runs",
        json={"message": "午餐吃苹果 80 千卡，然后根据今天记录给我建议"},
    )
    assert created.status_code == 200, created.text
    run = created.json()
    assert run["status"] == "waiting_for_user"
    assert run["verification"]["decision"] == "wait_for_user"
    assert len(run["candidates"]) == 1

    candidate = run["candidates"][0]
    confirmed = request(
        session,
        "POST",
        f"/api/v1/agent/confirmations/{candidate['candidate_id']}",
        headers={"Idempotency-Key": f"blackbox-{suffix}"},
        json={
            "confirmation_token": candidate["confirmation_token"],
            "kind": candidate["kind"],
            "payload": candidate["payload"],
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["resume_available"] is True

    resumed = request(
        session,
        "POST",
        f"/api/v1/agent/runs/{run['run_id']}/resume",
    )
    assert resumed.status_code == 200, resumed.text
    result = resumed.json()
    assert result["status"] == "completed"
    assert result["answer"]
    assert result["verification"]["decision"] == "done"
    assert any(item["tool"] == "recommendation.generate" for item in result["step_results"])

    trace = request(session, "GET", f"/api/v1/agent/runs/{run['run_id']}")
    assert trace.status_code == 200, trace.text
    assert trace.json()["resume_count"] == 1
    assert trace.json()["checkpoint_status"] == "consumed"


@allure.epic("Journey network black-box")
@allure.feature("Multi-Agent compound demo")
def test_multi_agent_food_activity_weekly_summary_over_real_http() -> None:
    session = requests.Session()
    suffix = uuid.uuid4().hex[:10]
    registered = request(
        session,
        "POST",
        "/api/v1/auth/register",
        json={
            "email": f"multi-agent-{suffix}@example.com",
            "username": f"multi_agent_{suffix}",
            "password": "JourneyBlackbox2026",
            "display_name": "Multi-Agent Demo",
        },
    )
    assert registered.status_code == 201, registered.text
    session.headers.update({"Authorization": f"Bearer {registered.json()['access_token']}"})

    created = request(
        session,
        "POST",
        "/api/v1/agent/runs",
        json={"message": "今天中午吃了一份牛肉面，晚上跑了5公里，我这周减脂情况怎么样？"},
    )
    assert created.status_code == 200, created.text
    run = created.json()
    assert run["status"] == "waiting_for_user"
    assert run["selected_agents"] == [
        "orchestrator",
        "record_agent",
        "journey_summary_agent",
        "health_knowledge_agent",
    ]
    assert {item["kind"] for item in run["candidates"]} == {"food", "activity"}

    for index, candidate in enumerate(run["candidates"]):
        confirmed = request(
            session,
            "POST",
            f"/api/v1/agent/confirmations/{candidate['candidate_id']}",
            headers={"Idempotency-Key": f"multi-agent-{suffix}-{index}"},
            json={
                "confirmation_token": candidate["confirmation_token"],
                "kind": candidate["kind"],
                "payload": candidate["payload"],
            },
        )
        assert confirmed.status_code == 201, confirmed.text

    resumed = request(session, "POST", f"/api/v1/agent/runs/{run['run_id']}/resume")
    assert resumed.status_code == 200, resumed.text
    result = resumed.json()
    assert result["status"] == "completed"
    assert re.search(r"(?:近|过去(?:的)?)\s*7\s*天", result["answer"])
    assert any(item["tool"] == "weekly_summary.generate" for item in result["step_results"])

    home = request(session, "GET", "/api/v1/home/today")
    assert home.status_code == 200, home.text
    assert home.json()["counts"]["food"] == 1
    assert home.json()["counts"]["activity"] == 1
    journey = request(session, "GET", "/api/v1/journey?limit=7")
    assert journey.status_code == 200, journey.text
    assert journey.json()["items"]

    trace = request(session, "GET", f"/api/v1/agent/runs/{run['run_id']}")
    assert trace.status_code == 200, trace.text
    payload = trace.json()
    assert payload["checkpoint_status"] == "consumed"
    assert {item["specialist"] for item in payload["tools"]} >= {
        "orchestrator",
        "record_agent",
        "journey_summary_agent",
        "health_knowledge_agent",
    }
