from fastapi.testclient import TestClient


def test_register_and_login_with_email_or_username(client: TestClient, register_user) -> None:
    account = register_user(email="Case@Test.Example", username="Case_User")
    user_id = account["tokens"]["user"]["id"]

    for identifier in ("case@test.example", "case_user"):
        response = client.post(
            "/api/v1/auth/login",
            json={"identifier": identifier, "password": account["payload"]["password"]},
        )
        assert response.status_code == 200
        assert response.json()["user"]["id"] == user_id


def test_duplicate_email_and_username_are_rejected(client: TestClient, register_user) -> None:
    account = register_user(email="duplicate@example.com", username="duplicate_user")
    base = account["payload"]

    email_duplicate = client.post(
        "/api/v1/auth/register",
        json={**base, "username": "another_user"},
    )
    assert email_duplicate.status_code == 409
    assert email_duplicate.json()["error"]["code"] == "email_taken"

    username_duplicate = client.post(
        "/api/v1/auth/register",
        json={**base, "email": "another@example.com"},
    )
    assert username_duplicate.status_code == 409
    assert username_duplicate.json()["error"]["code"] == "username_taken"


def test_refresh_rotation_and_logout_revoke_sessions(client: TestClient, register_user) -> None:
    account = register_user()
    original_refresh = account["tokens"]["refresh_token"]

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != original_refresh

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh})
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "refresh_token_reused"

    rejected_new_token = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated.json()["refresh_token"]},
    )
    assert rejected_new_token.status_code == 401

    fresh_login = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": account["payload"]["username"],
            "password": account["payload"]["password"],
        },
    ).json()
    headers = {"Authorization": f"Bearer {fresh_login['access_token']}"}
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_validation_and_auth_errors_use_stable_envelope(client: TestClient) -> None:
    validation = client.post("/api/v1/auth/register", json={})
    assert validation.status_code == 422
    assert validation.json()["error"]["code"] == "validation_error"
    assert validation.json()["request_id"] == validation.headers["X-Request-ID"]

    request_id = "client-trace-123"
    unauthorized = client.get("/api/v1/profile", headers={"X-Request-ID": request_id})
    assert unauthorized.status_code == 401
    assert unauthorized.json()["request_id"] == request_id


def test_cors_allows_contract_headers_for_local_web(client: TestClient) -> None:
    response = client.options(
        "/api/v1/food-records",
        headers={
            "Origin": "http://localhost:8081",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": (
                "authorization,content-type,idempotency-key,x-request-id"
            ),
        },
    )
    assert response.status_code == 200
    allowed = response.headers["Access-Control-Allow-Headers"].lower()
    assert "idempotency-key" in allowed

    actual = client.get(
        "/api/v1/profile",
        headers={"Origin": "http://localhost:8081"},
    )
    assert actual.status_code == 401
    assert "x-request-id" in actual.headers["Access-Control-Expose-Headers"].lower()

    e2e_preflight = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://127.0.0.1:4173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert e2e_preflight.status_code == 200
    assert e2e_preflight.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:4173"


def test_password_failures_lock_known_account(client: TestClient, register_user) -> None:
    account = register_user()
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"identifier": account["payload"]["email"], "password": "WrongPass2026"},
        )
        assert response.status_code == 401
    locked = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": account["payload"]["email"],
            "password": account["payload"]["password"],
        },
    )
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "account_locked"
