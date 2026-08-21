from fastapi.testclient import TestClient


def auth_headers(account: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {account['tokens']['access_token']}"}


def version_headers(account: dict, version: int) -> dict[str, str]:
    return {**auth_headers(account), "If-Match-Version": str(version)}


def test_profile_is_single_owned_resource_and_goal_is_upserted(
    client: TestClient, register_user
) -> None:
    account = register_user()

    updated = client.patch(
        "/api/v1/profile",
        headers=version_headers(account, 1),
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
        headers=version_headers(account, 0),
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
        headers=version_headers(account, goal.json()["version"]),
        json={"kind": "maintain", "starts_on": "2026-07-18"},
    )
    assert replaced.status_code == 200
    assert replaced.json()["id"] == first_goal_id
    assert replaced.json()["kind"] == "maintain"


def test_profile_rejects_unknown_timezone(client: TestClient, register_user) -> None:
    account = register_user()
    response = client.patch(
        "/api/v1/profile",
        headers=version_headers(account, 1),
        json={"timezone": "Mars/Olympus"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
