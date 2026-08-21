from datetime import UTC, datetime

from fastapi.testclient import TestClient


def auth(account: dict, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {account['tokens']['access_token']}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def test_profile_goal_agent_records_home_journey_recommendation_and_weekly_summary(
    client: TestClient,
    register_user,
    seeded_knowledge,
) -> None:
    """Core demo flow through public HTTP contracts with Mock Agent only."""
    account = register_user(display_name="Stage 7 E2E")
    headers = auth(account)
    now = datetime.now(UTC)

    profile = client.patch(
        "/api/v1/profile",
        headers={**headers, "If-Match-Version": "1"},
        json={
            "display_name": "Stage 7 E2E",
            "timezone": "Asia/Shanghai",
            "locale": "zh-CN",
            "sex": "undisclosed",
            "height_cm": 170,
            "preferred_unit": "metric",
        },
    )
    assert profile.status_code == 200, profile.text

    goal = client.put(
        "/api/v1/goals/current",
        headers={**headers, "If-Match-Version": "0"},
        json={
            "kind": "maintain",
            "target_weight_kg": 65,
            "daily_energy_target_kcal": 2000,
            "starts_on": now.date().isoformat(),
        },
    )
    assert goal.status_code == 200, goal.text

    run = client.post(
        "/api/v1/agent/runs",
        headers=headers,
        json={"message": "午餐吃了鸡肉饭 520 千卡，然后跑步 30 分钟 240 千卡"},
    )
    assert run.status_code == 200, run.text
    candidates = run.json()["candidates"]
    assert {candidate["kind"] for candidate in candidates} == {"food", "activity"}

    before = client.get("/api/v1/home/today", headers=headers).json()
    assert before["counts"]["food"] == before["counts"]["activity"] == 0

    for candidate in candidates:
        confirmed = client.post(
            f"/api/v1/agent/confirmations/{candidate['candidate_id']}",
            headers=auth(account, f"e2e-confirm-{candidate['candidate_id']}"),
            json={
                "confirmation_token": candidate["confirmation_token"],
                "kind": candidate["kind"],
                "payload": candidate["payload"],
            },
        )
        assert confirmed.status_code == 201, confirmed.text
        assert confirmed.json()["record"]["source"] == "agent"

    weight = client.post(
        "/api/v1/weight-records",
        headers=auth(account, "e2e-weight"),
        json={
            "measured_at": now.isoformat(),
            "weight_kg": 65,
            "source": "manual",
        },
    )
    assert weight.status_code == 201, weight.text

    home = client.get("/api/v1/home/today", headers=headers)
    assert home.status_code == 200
    assert home.json()["counts"] == {"food": 1, "activity": 1, "weight": 1}
    assert home.json()["intake_kcal"] == 520
    assert home.json()["activity_kcal"] == 240

    journey = client.get("/api/v1/journey?limit=7", headers=headers)
    assert journey.status_code == 200
    assert any(day["food_records"] and day["activity_records"] for day in journey.json()["items"])

    for message, expected_nodes in (
        (
            "根据今天记录给我建议",
            {
                "recommendation.context",
                "recommendation.retrieve",
                "recommendation.generate",
            },
        ),
        (
            "请生成本周总结",
            {
                "weekly_summary.context",
                "weekly_summary.retrieve",
                "weekly_summary.generate",
            },
        ),
    ):
        response = client.post("/api/v1/agent/runs", headers=headers, json={"message": message})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["answer"] and body["citations"]
        assert body["usage"]["provider"] == "mock"
        assert body["usage"]["estimated_cost_usd"] == 0
        trace = client.get(f"/api/v1/agent/runs/{body['run_id']}", headers=headers)
        assert expected_nodes <= {tool["tool_name"] for tool in trace.json()["tools"]}

    unconfirmed = client.post(
        "/api/v1/agent/runs",
        headers=headers,
        json={"message": "加餐吃了苹果 88 千卡"},
    )
    assert unconfirmed.status_code == 200
    assert unconfirmed.json()["candidates"]
    after = client.get("/api/v1/home/today", headers=headers).json()
    assert after["counts"] == {"food": 1, "activity": 1, "weight": 1}
