import base64
import json
from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import engine
from app.core.settings import get_settings
from app.media.food_image import FoodImageInvocation
from app.models.agent import AgentRun, AgentToolRun
from app.models.food_record import FoodRecord
from app.schemas.media import FoodImageEstimate

JPEG_BYTES = b"\xff\xd8\xff\xe0journey-synthetic-food-image\xff\xd9"
JPEG_BASE64 = base64.b64encode(JPEG_BYTES).decode("ascii")


def auth(account: dict, key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {account['tokens']['access_token']}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


def image_request(**overrides) -> dict:
    return {
        "image_base64": JPEG_BASE64,
        "media_type": "image/jpeg",
        "width": 640,
        "height": 480,
        "meal_type_hint": "lunch",
        "note": "合成测试鸡肉饭",
        "confirm_upload": True,
        **overrides,
    }


def test_mock_food_image_candidate_requires_correction_and_confirmation(
    client: TestClient, register_user
) -> None:
    account = register_user()
    response = client.post(
        "/api/v1/food-images/analyses",
        headers=auth(account),
        json=image_request(
            scale_reference_type="plate_diameter",
            scale_reference_size_cm=24,
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "candidate"
    assert body["fallback_used"] is True
    assert body["image_retained"] is False
    assert body["usage"]["provider"] == "mock"
    assert body["usage"]["estimated_cost_usd"] == 0
    assert body["estimate"]["needs_user_correction"] is True
    assert body["estimate"]["energy_min_kcal"] <= body["estimate"]["energy_kcal"]
    assert body["estimate"]["energy_kcal"] <= body["estimate"]["energy_max_kcal"]
    assert "未真实识别图片" in body["candidate"]["explanation"]

    with Session(engine) as db:
        assert db.query(FoodRecord).count() == 0
        run = db.scalar(select(AgentRun).where(AgentRun.id == body["analysis_id"]))
        assert run is not None
        assert run.intents == ["food_image"]
        trace = db.scalar(select(AgentToolRun).where(AgentToolRun.run_id == run.id))
        assert trace is not None
        stored_metadata = json.dumps({"input": trace.input_summary, "output": trace.output_summary})
        assert JPEG_BASE64 not in stored_metadata
        assert "journey-synthetic-food-image" not in stored_metadata
        assert trace.output_summary["image_retained"] is False
        assert trace.input_summary["scale_reference_type"] == "plate_diameter"
        assert trace.input_summary["scale_reference_size_cm"] == 24
        assert trace.output_summary["scale_reference_used"] is False

    candidate = body["candidate"]
    corrected = {
        **candidate["payload"],
        "name": "用户校正鸡肉饭",
        "energy_kcal": 520,
        "portion_amount": 1.5,
        "portion_unit": "碗",
    }
    confirmed = client.post(
        f"/api/v1/agent/confirmations/{candidate['candidate_id']}",
        headers=auth(account, "food-image-confirm-1"),
        json={
            "confirmation_token": candidate["confirmation_token"],
            "kind": "food",
            "payload": corrected,
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["record"]["name"] == "用户校正鸡肉饭"
    assert confirmed.json()["record"]["energy_kcal"] == 520
    assert confirmed.json()["record"]["source"] == "image"
    with Session(engine) as db:
        assert db.query(FoodRecord).count() == 1


def test_food_image_rejects_invalid_bytes_dimensions_and_missing_consent(
    client: TestClient, register_user
) -> None:
    account = register_user()
    invalid_base64 = client.post(
        "/api/v1/food-images/analyses",
        headers=auth(account),
        json=image_request(image_base64="not-valid-base64!!!!"),
    )
    assert invalid_base64.status_code == 422
    assert invalid_base64.json()["error"]["code"] == "invalid_food_image_base64"

    mismatch = client.post(
        "/api/v1/food-images/analyses",
        headers=auth(account),
        json=image_request(media_type="image/png"),
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "food_image_type_mismatch"

    dimensions = client.post(
        "/api/v1/food-images/analyses",
        headers=auth(account),
        json=image_request(width=5000),
    )
    assert dimensions.status_code == 422
    assert dimensions.json()["error"]["code"] == "food_image_dimensions_exceeded"

    missing_consent = client.post(
        "/api/v1/food-images/analyses",
        headers=auth(account),
        json=image_request(confirm_upload=False),
    )
    assert missing_consent.status_code == 422
    assert JPEG_BASE64 not in missing_consent.text

    missing_reference_size = client.post(
        "/api/v1/food-images/analyses",
        headers=auth(account),
        json=image_request(scale_reference_type="plate_diameter"),
    )
    assert missing_reference_size.status_code == 422

    invalid_reference_size = client.post(
        "/api/v1/food-images/analyses",
        headers=auth(account),
        json=image_request(
            scale_reference_type="bowl_diameter",
            scale_reference_size_cm=7,
        ),
    )
    assert invalid_reference_size.status_code == 422

    conflicting_card_size = client.post(
        "/api/v1/food-images/analyses",
        headers=auth(account),
        json=image_request(
            scale_reference_type="journey_card",
            scale_reference_size_cm=9,
        ),
    )
    assert conflicting_card_size.status_code == 422


def test_food_image_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/food-images/analyses", json=image_request())
    assert response.status_code == 401


def test_nonfood_and_provider_failure_return_manual_fallback(
    client: TestClient, register_user, monkeypatch
) -> None:
    account = register_user()
    nonfood = FoodImageEstimate(
        is_food=False,
        items=[],
        confidence="low",
        assumptions=["没有可靠识别到食物"],
    )
    monkeypatch.setattr(
        "app.media.food_image.MockFoodImageAnalyzer.analyze",
        lambda self, **kwargs: FoodImageInvocation(
            output=nonfood,
            provider="mock",
            model=self.model,
            input_tokens=0,
            output_tokens=0,
            latency_ms=1,
            estimated_cost_usd=0,
            fallback_used=True,
        ),
    )
    response = client.post(
        "/api/v1/food-images/analyses", headers=auth(account), json=image_request()
    )
    assert response.status_code == 200
    assert response.json()["status"] == "manual_required"
    assert response.json()["candidate"] is None

    def unavailable(self, **kwargs):
        raise TimeoutError("synthetic timeout")

    monkeypatch.setattr("app.media.food_image.MockFoodImageAnalyzer.analyze", unavailable)
    response = client.post(
        "/api/v1/food-images/analyses", headers=auth(account), json=image_request()
    )
    assert response.status_code == 200
    assert response.json()["status"] == "manual_required"
    assert response.json()["fallback_used"] is True


def test_food_image_feature_flag_has_manual_fallback_message(
    client: TestClient, register_user, monkeypatch
) -> None:
    account = register_user()
    disabled = replace(get_settings(), food_image_analysis_enabled=False)
    monkeypatch.setattr("app.media.food_image.get_settings", lambda: disabled)
    response = client.post(
        "/api/v1/food-images/analyses", headers=auth(account), json=image_request()
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "food_image_analysis_disabled"
    assert "manual food entry" in response.json()["error"]["message"]


def test_external_image_cannot_reuse_text_consent_or_construct_provider(
    client: TestClient, register_user, monkeypatch
) -> None:
    account = register_user()
    settings = replace(get_settings(), food_image_provider="qwen")
    monkeypatch.setattr("app.media.food_image.get_settings", lambda: settings)
    constructors = []
    monkeypatch.setattr(
        "app.media.food_image.LangChainLiteLLMFoodImageAnalyzer",
        lambda *args: constructors.append(True),
    )
    response = client.post(
        "/api/v1/food-images/analyses", headers=auth(account), json=image_request()
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "food_image_external_disabled"
    assert constructors == []
    with Session(engine) as db:
        assert db.query(AgentRun).count() == 0
