#!/usr/bin/env python3
"""Run a zero-model-cost smoke test against a Journey staging API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


BASE_URL = os.environ["STAGING_API_URL"].rstrip("/")
IDENTIFIER = os.environ["STAGING_TEST_IDENTIFIER"]
PASSWORD = os.environ["STAGING_TEST_PASSWORD"]


def request(path: str, *, token: str | None = None, payload: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode() if payload is not None else None
    method = "POST" if payload is not None else "GET"
    call = urllib.request.Request(f"{BASE_URL}{path}", body, headers, method=method)
    try:
        with urllib.request.urlopen(call, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"{path} returned HTTP {error.code}") from error


ready = request("/health/ready")
assert ready == {
    "status": "ok",
    "service": "journey-api",
    "environment": "staging",
    "database": "ok",
}
session = request(
    "/api/v1/auth/login",
    payload={"identifier": IDENTIFIER, "password": PASSWORD},
)
token = session["access_token"]
home = request("/api/v1/home/today", token=token)
agent = request(
    "/api/v1/agent/runs",
    token=token,
    payload={"message": "根据今天记录给我一条建议"},
)
assert agent["usage"]["provider"] == "mock"
assert agent["usage"]["estimated_cost_usd"] == 0
trace = request(f"/api/v1/agent/runs/{agent['run_id']}", token=token)
assert trace["prompt_version"] == "journey-agent-1.0.0"
assert trace["schema_version"] == "journey-agent-schema-1"
assert trace["knowledge_version"] == "journey-core-1.0.0"
print(
    json.dumps(
        {
            "ready": ready["status"],
            "home_date": home["date"],
            "provider": agent["usage"]["provider"],
            "cost_usd": agent["usage"]["estimated_cost_usd"],
            "prompt_version": trace["prompt_version"],
        },
        ensure_ascii=False,
    )
)
