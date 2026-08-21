from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient


def auth(account: dict, version: int | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {account['tokens']['access_token']}"}
    if version is not None:
        headers["If-Match-Version"] = str(version)
    return headers


def test_profile_and_goal_require_current_versions(client: TestClient, register_user) -> None:
    account = register_user()

    profile = client.get("/api/v1/profile", headers=auth(account)).json()
    updated = client.patch(
        "/api/v1/profile",
        headers=auth(account, profile["version"]),
        json={"display_name": "设备 A"},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == profile["version"] + 1

    stale = client.patch(
        "/api/v1/profile",
        headers=auth(account, profile["version"]),
        json={"display_name": "设备 B"},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "sync_conflict"
    details = stale.json()["error"]["details"]
    assert details["actual_version"] == updated.json()["version"]
    assert details["server"]["display_name"] == "设备 A"

    created_goal = client.put(
        "/api/v1/goals/current",
        headers=auth(account, 0),
        json={"kind": "maintain", "starts_on": "2026-08-05"},
    )
    assert created_goal.status_code == 200
    assert created_goal.json()["version"] == 1

    goal_updated = client.put(
        "/api/v1/goals/current",
        headers=auth(account, 1),
        json={"kind": "gain_muscle", "starts_on": "2026-08-05"},
    )
    assert goal_updated.status_code == 200
    assert goal_updated.json()["version"] == 2

    goal_stale = client.put(
        "/api/v1/goals/current",
        headers=auth(account, 1),
        json={"kind": "lose_fat", "starts_on": "2026-08-05"},
    )
    assert goal_stale.status_code == 409
    assert goal_stale.json()["error"]["details"]["server"]["kind"] == "gain_muscle"


def test_concurrent_first_goal_creation_returns_stable_conflict(
    client: TestClient, register_user
) -> None:
    account = register_user()

    def create(kind: str):
        return client.put(
            "/api/v1/goals/current",
            headers=auth(account, 0),
            json={"kind": kind, "starts_on": "2026-08-10"},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(create, ["maintain", "gain_muscle"]))

    assert sorted(response.status_code for response in responses) == [200, 409]
    saved = next(response.json() for response in responses if response.status_code == 200)
    conflict = next(response.json() for response in responses if response.status_code == 409)
    assert conflict["error"]["code"] == "sync_conflict"
    assert conflict["error"]["details"]["actual_version"] == saved["version"]
    assert conflict["error"]["details"]["server"]["id"] == saved["id"]


def test_record_update_and_delete_never_silently_overwrite(
    client: TestClient, register_user
) -> None:
    account = register_user()
    created = client.post(
        "/api/v1/weight-records",
        headers={**auth(account), "Idempotency-Key": "sync-weight-create"},
        json={"measured_at": "2026-08-05T07:00:00+08:00", "weight_kg": 65},
    )
    assert created.status_code == 201
    record = created.json()
    assert record["version"] == 1

    updated = client.patch(
        f"/api/v1/weight-records/{record['id']}",
        headers=auth(account, record["version"]),
        json={"weight_kg": 64.8},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    stale_update = client.patch(
        f"/api/v1/weight-records/{record['id']}",
        headers=auth(account, 1),
        json={"weight_kg": 66},
    )
    assert stale_update.status_code == 409
    assert stale_update.json()["error"]["details"]["server"]["weight_kg"] == 64.8

    stale_delete = client.delete(f"/api/v1/weight-records/{record['id']}", headers=auth(account, 1))
    assert stale_delete.status_code == 409

    deleted = client.delete(f"/api/v1/weight-records/{record['id']}", headers=auth(account, 2))
    assert deleted.status_code == 200
