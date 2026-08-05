import json
import os
import time
import uuid

import allure
import requests

BASE_URL = os.getenv("BLACKBOX_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECONDS = 15


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
