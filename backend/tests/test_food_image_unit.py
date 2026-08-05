from dataclasses import replace

from app.core.settings import get_settings
from app.media.food_image import (
    LangChainLiteLLMFoodImageAnalyzer,
    _safe_food_image_estimate,
)
from app.schemas.media import FoodImageEstimate


def test_qwen_vision_uses_separate_langchain_litellm_route(monkeypatch) -> None:
    router_calls: list[dict] = []
    chat_calls: list[dict] = []
    structured_calls: list[dict] = []
    invoked_messages: list = []

    class FakeRaw:
        usage_metadata = {"input_tokens": 120, "output_tokens": 60}

    class FakeStructuredModel:
        def invoke(self, messages):
            invoked_messages.extend(messages)
            return {
                "parsed": FoodImageEstimate(
                    is_food=True,
                    name="合成鸡肉饭",
                    items=[
                        {
                            "name": "合成鸡肉饭",
                            "portion_amount": 1,
                            "portion_unit": "份",
                            "energy_kcal": 420,
                        }
                    ],
                    meal_type="lunch",
                    portion_amount=1,
                    portion_unit="份",
                    energy_kcal=420,
                    energy_min_kcal=280,
                    energy_max_kcal=600,
                    confidence="low",
                    assumptions=["合成测试"],
                ),
                "raw": FakeRaw(),
            }

    class FakeLiteLLMRouter:
        def __init__(self, **kwargs):
            router_calls.append(kwargs)

    class FakeChatLiteLLMRouter:
        def __init__(self, **kwargs):
            chat_calls.append(kwargs)

        def with_structured_output(self, schema, **kwargs):
            assert schema is FoodImageEstimate
            structured_calls.append(kwargs)
            return FakeStructuredModel()

    monkeypatch.setattr("app.media.food_image.LiteLLMRouter", FakeLiteLLMRouter)
    monkeypatch.setattr("app.media.food_image.ChatLiteLLMRouter", FakeChatLiteLLMRouter)
    settings = replace(
        get_settings(),
        food_image_provider="qwen",
        food_image_api_key="test-placeholder-qwen-vision-key",
        food_image_api_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        food_image_model="qwen3.7-flash",
        food_image_input_usd_per_million=1,
        food_image_output_usd_per_million=2,
        food_image_daily_budget_usd=1,
        food_image_external_upload_confirmed=True,
    )

    analyzer = LangChainLiteLLMFoodImageAnalyzer(settings)
    result = analyzer.analyze(
        data_url="data:image/jpeg;base64,/9j/4EpvdXJuZXk=",
        note="合成测试",
        meal_type_hint="lunch",
        scale_reference_type="journey_card",
        scale_reference_size_cm=None,
    )

    params = router_calls[0]["model_list"][0]["litellm_params"]
    assert params["model"] == "openai/qwen3.7-flash"
    assert params["api_base"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert params["extra_body"] == {"enable_thinking": False}
    assert params["api_key"] == "test-placeholder-qwen-vision-key"
    assert router_calls[0]["num_retries"] == 0
    assert chat_calls[0]["model"] == "journey-food-image-qwen-qwen3.7-flash"
    assert structured_calls == [{"method": "json_mode", "include_raw": True}]
    assert invoked_messages[1].content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "9×5 cm" in invoked_messages[1].content[0]["text"]
    assert result.output is not None
    assert result.output.needs_user_correction is True
    assert result.input_tokens == 120
    assert result.output_tokens == 60
    assert result.estimated_cost_usd == 0.00024


def test_qwen_invalid_enum_and_narrow_range_are_safely_normalized() -> None:
    class FakeRaw:
        content = """{
          "is_food": true,
          "name": "苹果",
          "canonical_name_en": "apple",
          "items": [{
            "name": "苹果",
            "canonical_name_en": "apple",
            "portion_amount": 120,
            "portion_unit": "g",
            "energy_kcal": 62
          }],
          "meal_type": "unknown",
          "portion_amount": 120,
          "portion_unit": "g",
          "energy_kcal": null,
          "energy_min_kcal": 60,
          "energy_max_kcal": 64,
          "confidence": "high",
          "assumptions": [],
          "needs_user_correction": false
        }"""

    estimate = _safe_food_image_estimate(None, FakeRaw())

    assert estimate.confidence == "medium"
    assert estimate.meal_type == "other"
    assert estimate.needs_user_correction is True
    assert estimate.canonical_name_en == "apple"
    assert estimate.energy_min_kcal == 15.5
    assert estimate.energy_max_kcal == 124
    assert estimate.scale_reference_used is False
    assert "安全候选" in estimate.assumptions[-1]
