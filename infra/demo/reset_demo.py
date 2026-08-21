#!/usr/bin/env python3
"""Reset only the configured Journey demo account through public API v1."""

from __future__ import annotations

import json
import os
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone


BASE_URL = os.getenv("JOURNEY_API_URL", "http://127.0.0.1:8000").rstrip("/")
IDENTIFIER = os.getenv("JOURNEY_DEMO_IDENTIFIER", "demo@journey.local")
PASSWORD = os.environ["JOURNEY_DEMO_PASSWORD"]


def call(
    path: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict | None = None,
    idempotency_key: str | None = None,
    expected_version: int | None = None,
    allow_not_found: bool = False,
) -> dict | None:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    if expected_version is not None:
        headers["If-Match-Version"] = str(expected_version)
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(f"{BASE_URL}{path}", body, headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response) if response.status != 204 else None
    except urllib.error.HTTPError as error:
        if allow_not_found and error.code == 404:
            return None
        detail = error.read().decode(errors="replace")[:500]
        raise RuntimeError(f"{method} {path} returned HTTP {error.code}: {detail}") from error


def delete_records(token: str, resource: str) -> int:
    deleted = 0
    while True:
        page = call(f"/api/v1/{resource}?limit=100", token=token)
        assert page is not None
        items = page["items"]
        if not items:
            return deleted
        for item in items:
            call(
                f"/api/v1/{resource}/{item['id']}",
                method="DELETE",
                token=token,
                expected_version=item["version"],
            )
            deleted += 1


if os.getenv("RESET_CONFIRM") != "journey-demo-account":
    raise SystemExit("Refusing reset: set RESET_CONFIRM=journey-demo-account")

session = call(
    "/api/v1/auth/login",
    method="POST",
    payload={"identifier": IDENTIFIER, "password": PASSWORD},
)
assert session is not None
token = session["access_token"]
deleted = sum(
    delete_records(token, resource)
    for resource in ("food-records", "activity-records", "weight-records")
)

profile = call("/api/v1/profile", token=token)
assert profile is not None
call(
    "/api/v1/profile",
    method="PATCH",
    token=token,
    expected_version=profile["version"],
    payload={
        "display_name": "Journey 演示用户",
        "timezone": "Asia/Shanghai",
        "locale": "zh-CN",
        "sex": "undisclosed",
        "birth_date": "2000-01-01",
        "height_cm": 170,
        "preferred_unit": "metric",
    },
)
today = datetime.now(timezone.utc)
goal = call("/api/v1/goals/current", token=token, allow_not_found=True)
call(
    "/api/v1/goals/current",
    method="PUT",
    token=token,
    expected_version=goal["version"] if goal else 0,
    payload={
        "kind": "lose_fat",
        "target_weight_kg": 63,
        "daily_energy_target_kcal": 1900,
        "starts_on": today.date().isoformat(),
    },
)

run_id = uuid.uuid4().hex[:10]
records = [
    (
        "food-records",
        {
            "recorded_at": (today - timedelta(hours=5)).isoformat(),
            "meal_type": "lunch",
            "name": "鸡肉杂粮饭",
            "detail": "演示数据",
            "portion_amount": 1,
            "portion_unit": "份",
            "energy_kcal": 520,
            "protein_g": 36,
            "carbs_g": 62,
            "fat_g": 14,
            "source": "manual",
        },
    ),
    (
        "food-records",
        {
            "recorded_at": (today - timedelta(hours=2)).isoformat(),
            "meal_type": "snack",
            "name": "原味酸奶",
            "detail": "演示数据",
            "portion_amount": 200,
            "portion_unit": "g",
            "energy_kcal": 148,
            "protein_g": 8,
            "carbs_g": 18,
            "fat_g": 5,
            "source": "manual",
        },
    ),
    (
        "activity-records",
        {
            "recorded_at": (today - timedelta(hours=3)).isoformat(),
            "name": "慢跑",
            "activity_type": "cardio",
            "duration_minutes": 32,
            "intensity": "moderate",
            "energy_kcal": 260,
            "note": "演示数据",
            "source": "manual",
        },
    ),
]
for index, (resource, payload) in enumerate(records):
    call(
        f"/api/v1/{resource}",
        method="POST",
        token=token,
        payload=payload,
        idempotency_key=f"demo-reset-{run_id}-{index}",
    )

for index, (days, weight) in enumerate(((6, 66.2), (3, 65.7), (0, 65.4))):
    call(
        "/api/v1/weight-records",
        method="POST",
        token=token,
        payload={
            "measured_at": (today - timedelta(days=days)).isoformat(),
            "weight_kg": weight,
            "note": "演示趋势数据",
            "source": "manual",
        },
        idempotency_key=f"demo-reset-{run_id}-weight-{index}",
    )

home = call("/api/v1/home/today", token=token)
journey = call("/api/v1/journey?limit=7", token=token)
assert home is not None and journey is not None
print(
    json.dumps(
        {
            "deleted": deleted,
            "seeded": len(records) + 3,
            "home": {
                "intake_kcal": home["intake_kcal"],
                "activity_kcal": home["activity_kcal"],
                "latest_weight_kg": home["latest_weight_kg"],
            },
            "journey_days": len(journey["items"]),
        },
        ensure_ascii=False,
    )
)
