from fastapi.testclient import TestClient


def auth_headers(account: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {account['tokens']['access_token']}"}


def test_profile_is_single_owned_resource_and_goal_is_upserted(
    client: TestClient, register_user
) -> None:
    account = register_user()
    headers = auth_headers(account)

    updated = client.patch(
        "/api/v1/profile",
        headers=headers,
        json={
            "display_name": "小旅",
            "timezone": "Asia/Shanghai",
            "height_cm": 172.5,
            "sex": "undisclosed",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "小旅"
    assert updated.json()["latest_weight_kg"] is None

    goal = client.put(
        "/api/v1/goals/current",
        headers=headers,
        json={
            "kind": "lose_fat",
            "target_weight_kg": 65,
            "daily_energy_target_kcal": 1900,
            "starts_on": "2026-07-17",
            "target_date": "2026-12-31",
        },
    )
    assert goal.status_code == 200
    first_goal_id = goal.json()["id"]

    replaced = client.put(
        "/api/v1/goals/current",
        headers=headers,
        json={"kind": "maintain", "starts_on": "2026-07-18"},
    )
    assert replaced.status_code == 200
    assert replaced.json()["id"] == first_goal_id
    assert replaced.json()["kind"] == "maintain"


def test_profile_rejects_unknown_timezone(client: TestClient, register_user) -> None:
    account = register_user()
    response = client.patch(
        "/api/v1/profile",
        headers=auth_headers(account),
        json={"timezone": "Mars/Olympus"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
