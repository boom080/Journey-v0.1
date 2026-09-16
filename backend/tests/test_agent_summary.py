import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.agent.skills.journey_coach import requires_coaching_fallback
from app.core.database import SessionLocal
from app.models.agent import AgentRun, AgentSummaryCache, AgentToolRun
from app.schemas.agent import AgentSummaryGenerated


def _auth(account: dict, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {account['tokens']['access_token']}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


def _food(client: TestClient, account: dict, *, at: datetime, kcal: float, key: str) -> None:
    response = client.post(
        "/api/v1/food-records",
        headers=_auth(account, key),
        json={
            "recorded_at": at.isoformat(),
            "meal_type": "lunch",
            "name": "测试餐",
            "energy_kcal": kcal,
        },
    )
    assert response.status_code == 201, response.text


def test_coach_quality_gate_rejects_repetitive_advice() -> None:
    repetitive = AgentSummaryGenerated(
        headline="近7天已有2天记录，可以选择下一步行动。",
        key_findings=[
            {"title": "记录情况", "evidence": "近7天有2天记录。", "interpretation": "记录较少。"},
            {"title": "运动情况", "evidence": "近7天有1次运动。", "interpretation": "可以继续。"},
        ],
        next_7_days=[
            {
                "title": "继续保持记录",
                "plan": "接下来7天继续保持记录。",
                "reason": "让模式更容易被看见。",
                "success_metric": "7天后回顾1次。",
            },
            {
                "title": "选择一个小调整",
                "plan": "接下来7天选择1个小调整。",
                "reason": "这样更容易执行。",
                "success_metric": "7天后完成1项。",
            },
        ],
    )
    assert requires_coaching_fallback(repetitive, 7) is True


def test_thirty_day_summary_uses_backend_statistics_and_fingerprint_cache(
    client: TestClient, register_user
) -> None:
    account = register_user()
    headers = _auth(account)
    now = datetime.now(UTC)
    goal = client.put(
        "/api/v1/goals/current",
        headers={**headers, "If-Match-Version": "0"},
        json={
            "kind": "lose_fat",
            "target_weight_kg": 65,
            "daily_energy_target_kcal": 2000,
            "starts_on": now.date().isoformat(),
        },
    )
    assert goal.status_code == 200, goal.text

    _food(client, account, at=now - timedelta(days=10), kcal=600, key="summary-food-old")
    _food(client, account, at=now, kcal=500, key="summary-food-new")
    for days_ago in range(1, 7):
        _food(
            client,
            account,
            at=now - timedelta(days=days_ago),
            kcal=100,
            key=f"summary-food-day-{days_ago}",
        )
    activity = client.post(
        "/api/v1/activity-records",
        headers=_auth(account, "summary-activity"),
        json={
            "recorded_at": now.isoformat(),
            "name": "慢跑",
            "duration_minutes": 30,
            "intensity": "moderate",
            "energy_kcal": 200,
        },
    )
    assert activity.status_code == 201, activity.text
    for index, (measured_at, weight) in enumerate(((now - timedelta(days=10), 70), (now, 69.5))):
        response = client.post(
            "/api/v1/weight-records",
            headers=_auth(account, f"summary-weight-{index}"),
            json={"measured_at": measured_at.isoformat(), "weight_kg": weight},
        )
        assert response.status_code == 201, response.text

    first = client.post("/api/v1/agent/summaries/30-day", headers=headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["period_days"] == 30
    assert body["cache_hit"] is False
    month = body["statistics"]["last_30_days"]
    assert {
        key: month[key]
        for key in (
            "record_count",
            "total_intake_kcal",
            "total_activity_kcal",
            "days_with_records",
            "weight_change_kg",
        )
    } == {
        "record_count": 11,
        "total_intake_kcal": 1700,
        "total_activity_kcal": 200,
        "days_with_records": 8,
        "weight_change_kg": -0.5,
    }
    week = body["statistics"]["last_7_days"]
    assert {
        key: week[key]
        for key in (
            "record_count",
            "total_intake_kcal",
            "total_activity_kcal",
            "days_with_records",
            "weight_change_kg",
        )
    } == {
        "record_count": 9,
        "total_intake_kcal": 1100,
        "total_activity_kcal": 200,
        "days_with_records": 7,
        "weight_change_kg": None,
    }
    assert body["statistics"]["goal"]["kind"] == "lose_fat"
    assert len(body["content"]["key_findings"]) == 3
    assert 2 <= len(body["content"]["next_7_days"]) <= 3
    assert all(
        set(item) == {"title", "evidence", "interpretation"}
        for item in body["content"]["key_findings"]
    )
    assert all(
        set(item) == {"title", "plan", "reason", "success_metric"}
        and any(character.isdigit() for character in item["success_metric"])
        for item in body["content"]["next_7_days"]
    )
    assert "先补齐可判断的数据" in {item["title"] for item in body["content"]["next_7_days"]}
    assert body["citations"] == []

    second = client.post("/api/v1/agent/summaries/30-day", headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["cache_hit"] is True
    assert second.json()["generated_at"] == body["generated_at"]
    assert second.json()["content"] == body["content"]
    assert second.json()["usage"]["input_tokens"] == 0

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AgentSummaryCache)) == 1
        assert db.scalar(select(func.count()).select_from(AgentRun)) == 1
        traces = list(db.scalars(select(AgentToolRun).order_by(AgentToolRun.created_at.asc())))
        assert [trace.tool_name for trace in traces] == [
            "monthly_summary.statistics",
            "monthly_summary.retrieve",
            "monthly_summary.generate",
        ]
        assert traces[1].status == "skipped"
        assert traces[1].output_summary["chunk_count"] == 0
        assert traces[2].input_summary["raw_records_sent"] == 0
        assert traces[2].input_summary["llm_call_count"] == 1

    _food(client, account, at=now, kcal=100, key="summary-food-change")
    changed = client.post("/api/v1/agent/summaries/30-day", headers=headers)
    assert changed.status_code == 200, changed.text
    assert changed.json()["cache_hit"] is False
    assert changed.json()["statistics"]["last_30_days"]["record_count"] == 12
    assert changed.json()["statistics"]["last_30_days"]["total_intake_kcal"] == 1800
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AgentRun)) == 2

    deleted = client.delete("/api/v1/agent/privacy/data", headers=headers)
    assert deleted.status_code == 200, deleted.text
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AgentSummaryCache)) == 0


def test_thirty_day_summary_only_retrieves_knowledge_when_goal_data_needs_it(
    client: TestClient, register_user, seeded_knowledge
) -> None:
    account = register_user()
    headers = _auth(account)
    now = datetime.now(UTC)
    goal = client.put(
        "/api/v1/goals/current",
        headers={**headers, "If-Match-Version": "0"},
        json={"kind": "maintain", "starts_on": now.date().isoformat()},
    )
    assert goal.status_code == 200, goal.text
    for days_ago in range(14):
        _food(
            client,
            account,
            at=now - timedelta(days=days_ago),
            kcal=500,
            key=f"summary-knowledge-food-{days_ago}",
        )

    response = client.post("/api/v1/agent/summaries/30-day", headers=headers)
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        retrieval = db.scalar(
            select(AgentToolRun).where(AgentToolRun.tool_name == "monthly_summary.retrieve")
        )
        assert retrieval is not None
        assert retrieval.status == "completed"
        assert retrieval.output_summary["chunk_count"] > 0


def test_summary_periods_enforce_separate_recorded_day_thresholds(
    client: TestClient, register_user
) -> None:
    account = register_user()
    headers = _auth(account)
    now = datetime.now(UTC)
    _food(client, account, at=now, kcal=500, key="summary-threshold-day-0")

    insufficient_week = client.post("/api/v1/agent/summaries/7-day", headers=headers)
    assert insufficient_week.status_code == 422, insufficient_week.text
    week_error = insufficient_week.json()["error"]
    assert week_error["code"] == "summary_insufficient_recorded_days"
    assert week_error["details"] == {
        "period_days": 7,
        "days_with_records": 1,
        "minimum_days_with_records": 2,
        "remaining_days": 1,
    }

    _food(
        client,
        account,
        at=now - timedelta(days=1),
        kcal=450,
        key="summary-threshold-day-1",
    )
    week = client.post("/api/v1/agent/summaries/7-day", headers=headers)
    assert week.status_code == 200, week.text
    week_body = week.json()
    assert week_body["period_days"] == 7
    assert week_body["statistics"]["last_7_days"]["days_with_records"] == 2
    assert "无法评估" not in json.dumps(week_body["content"], ensure_ascii=False)
    week_actions = week_body["content"]["next_7_days"]
    assert {item["title"] for item in week_actions} >= {
        "先补齐可判断的数据",
        "把运动排进日历",
    }
    assert all(
        any(character.isdigit() for character in item["success_metric"]) for item in week_actions
    )

    _food(
        client,
        account,
        at=now - timedelta(days=10),
        kcal=600,
        key="summary-threshold-outside-week",
    )
    unchanged_week = client.post("/api/v1/agent/summaries/7-day", headers=headers)
    assert unchanged_week.status_code == 200, unchanged_week.text
    assert unchanged_week.json()["cache_hit"] is True
    assert unchanged_week.json()["statistics"]["last_30_days"]["record_count"] == 3

    insufficient_month = client.post("/api/v1/agent/summaries/30-day", headers=headers)
    assert insufficient_month.status_code == 422, insufficient_month.text
    assert insufficient_month.json()["error"]["details"]["minimum_days_with_records"] == 7

    for days_ago in range(2, 7):
        _food(
            client,
            account,
            at=now - timedelta(days=days_ago),
            kcal=400,
            key=f"summary-threshold-day-{days_ago}",
        )
    month = client.post("/api/v1/agent/summaries/30-day", headers=headers)
    assert month.status_code == 200, month.text
    assert month.json()["period_days"] == 30

    with SessionLocal() as db:
        periods = set(db.scalars(select(AgentSummaryCache.period_days)))
        assert periods == {7, 30}
