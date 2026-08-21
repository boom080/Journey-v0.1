from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient


def headers(account: dict, key: str | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {account['tokens']['access_token']}"}
    if key:
        result["Idempotency-Key"] = key
    return result


FOOD = {
    "recorded_at": "2026-07-17T12:30:00+08:00",
    "meal_type": "lunch",
    "name": "鸡胸肉饭",
    "portion_amount": 1,
    "portion_unit": "份",
    "energy_kcal": 520,
    "protein_g": 35,
    "carbs_g": 60,
    "fat_g": 12,
    "source": "manual",
}


def test_record_idempotency_conflict_and_concurrent_replay(
    client: TestClient, register_user
) -> None:
    account = register_user()
    request_headers = headers(account, "food-create-1")

    first = client.post("/api/v1/food-records", headers=request_headers, json=FOOD)
    replay = client.post("/api/v1/food-records", headers=request_headers, json=FOOD)
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]

    conflict = client.post(
        "/api/v1/food-records",
        headers=request_headers,
        json={**FOOD, "energy_kcal": 600},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"

    concurrent_headers = headers(account, "food-concurrent-1")
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda _: client.post(
                    "/api/v1/food-records", headers=concurrent_headers, json=FOOD
                ),
                range(2),
            )
        )
    assert {response.status_code for response in responses} == {201}
    assert len({response.json()["id"] for response in responses}) == 1

    listed = client.get("/api/v1/food-records", headers=headers(account)).json()
    assert listed["meta"]["total"] == 2


def test_ownership_crud_home_and_journey_are_deterministic(
    client: TestClient, register_user
) -> None:
    owner = register_user()
    stranger = register_user()
    owner_headers = headers(owner)
    profile = client.patch(
        "/api/v1/profile",
        headers={**owner_headers, "If-Match-Version": "1"},
        json={"sex": "male", "birth_date": "2000-08-13", "height_cm": 170},
    )
    assert profile.status_code == 200, profile.text

    food = client.post(
        "/api/v1/food-records",
        headers=headers(owner, "food-day-1"),
        json=FOOD,
    )
    activity = client.post(
        "/api/v1/activity-records",
        headers=headers(owner, "activity-day-1"),
        json={
            "recorded_at": "2026-07-17T18:00:00+08:00",
            "name": "慢跑",
            "activity_type": "running",
            "duration_minutes": 30,
            "intensity": "moderate",
            "energy_kcal": 240,
            "source": "manual",
        },
    )
    weight = client.post(
        "/api/v1/weight-records",
        headers=headers(owner, "weight-day-1"),
        json={
            "measured_at": "2026-07-17T07:00:00+08:00",
            "weight_kg": 70.5,
            "source": "manual",
        },
    )
    assert food.status_code == activity.status_code == weight.status_code == 201

    forbidden_by_ownership = client.patch(
        f"/api/v1/food-records/{food.json()['id']}",
        headers={**headers(stranger), "If-Match-Version": str(food.json()["version"])},
        json={"energy_kcal": 1},
    )
    assert forbidden_by_ownership.status_code == 404

    home = client.get("/api/v1/home/today?date=2026-07-17", headers=owner_headers)
    assert home.status_code == 200
    assert home.json()["intake_kcal"] == 520
    assert home.json()["activity_kcal"] == 240
    assert home.json()["net_kcal"] == 280
    assert home.json()["latest_weight_kg"] == 70.5
    assert home.json()["resting_energy"] == {
        "status": "available",
        "kcal_per_day": 1647.5,
        "formula": "mifflin-st-jeor-1990",
        "age_years": 25,
        "missing_fields": [],
        "note": "静息能量消耗预测值，不是代谢测量，也不等于包含日常活动和食物热效应的 TDEE。",
    }
    assert home.json()["estimated_energy_balance_kcal"] == -1367.5

    client.post(
        "/api/v1/food-records",
        headers=headers(owner, "food-day-2"),
        json={**FOOD, "recorded_at": "2026-07-16T12:00:00+08:00", "energy_kcal": 400},
    )
    first_page = client.get(
        "/api/v1/journey?start_date=2026-07-01&end_date=2026-07-31&limit=1",
        headers=owner_headers,
    ).json()
    assert first_page["items"][0]["date"] == "2026-07-17"
    assert first_page["has_more"] is True
    second_page = client.get(
        f"/api/v1/journey?start_date=2026-07-01&end_date=2026-07-31&limit=1&cursor={first_page['next_cursor']}",
        headers=owner_headers,
    ).json()
    assert second_page["items"][0]["date"] == "2026-07-16"


def test_invalid_record_parameters_are_rejected(client: TestClient, register_user) -> None:
    account = register_user()
    response = client.post(
        "/api/v1/activity-records",
        headers=headers(account),
        json={
            "recorded_at": "2026-07-17T12:00:00",
            "name": "Impossible",
            "duration_minutes": 0,
            "intensity": "extreme",
            "energy_kcal": -1,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
