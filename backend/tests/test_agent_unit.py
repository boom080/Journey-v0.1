import json
from dataclasses import replace
from pathlib import Path

import httpx
from openai import APIConnectionError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.intent_router import (
    ROUTER_PROMPT_VERSION,
    ROUTER_SYSTEM_PROMPT,
    deterministic_intent_plan,
)
from app.agent.model_router import (
    DEEPSEEK_API_BASE_URL,
    LangChainLiteLLMAdapter,
    MockModelAdapter,
    ModelAdapter,
    ModelRouter,
)
from app.agent.workflows import run_knowledge
from app.core.database import engine
from app.core.settings import get_settings
from app.knowledge.retriever import retrieve
from app.models.knowledge import KnowledgeChunk
from app.schemas.agent import FoodParsed

EVALS = Path(__file__).parent / "evals"


class UnavailableProviderAdapter(ModelAdapter):
    provider = "deepseek"

    def invoke_structured(self, **kwargs):
        raise APIConnectionError(request=httpx.Request("POST", "http://127.0.0.1:1"))


class SuccessfulProviderAdapter(ModelAdapter):
    provider = "deepseek"

    def invoke_structured(self, **kwargs):
        return kwargs["fallback_factory"](), 1_000_000, 1_000_000


class FailIfCalledAdapter(ModelAdapter):
    provider = "deepseek"

    def invoke_structured(self, **kwargs):
        raise AssertionError("no-context retrieval must not call a model")


def test_deepseek_v4_uses_official_endpoint_and_model_specific_thinking(monkeypatch) -> None:
    router_calls: list[dict] = []
    chat_calls: list[dict] = []
    structured_calls: list[dict] = []

    class FakeRaw:
        usage_metadata = {"input_tokens": 10, "output_tokens": 5}

    class FakeStructuredModel:
        def __init__(self, schema):
            self.schema = schema

        def invoke(self, messages):
            assert len(messages) == 2
            return {
                "parsed": self.schema(meal_type="other", name="测试", energy_kcal=100),
                "raw": FakeRaw(),
            }

    class FakeLiteLLMRouter:
        def __init__(self, **kwargs):
            router_calls.append(kwargs)

    class FakeChatLiteLLMRouter:
        def __init__(self, **kwargs):
            chat_calls.append(kwargs)

        def with_structured_output(self, schema, **kwargs):
            structured_calls.append(kwargs)
            return FakeStructuredModel(schema)

    monkeypatch.setattr("app.agent.model_router.LiteLLMRouter", FakeLiteLLMRouter)
    monkeypatch.setattr("app.agent.model_router.ChatLiteLLMRouter", FakeChatLiteLLMRouter)
    settings = replace(
        get_settings(),
        agent_provider="deepseek",
        agent_api_key="test-placeholder",
        agent_api_base_url=None,
        agent_default_model="deepseek-v4-flash",
        agent_model_map={"recommendation": "deepseek-v4-pro"},
        agent_daily_budget_usd=0.10,
    )
    adapter = LangChainLiteLLMAdapter(settings)

    for model in ("deepseek-v4-flash", "deepseek-v4-pro"):
        adapter.invoke_structured(
            model=model,
            schema=FoodParsed,
            system_prompt="test",
            user_prompt="test",
            fallback_factory=lambda: FoodParsed(
                meal_type="other", name="fallback", energy_kcal=100
            ),
        )

    deployments = {
        item["model_name"]: item["litellm_params"] for item in router_calls[0]["model_list"]
    }
    flash = deployments["journey-deepseek-deepseek-v4-flash"]
    pro = deployments["journey-deepseek-deepseek-v4-pro"]
    assert flash["api_base"] == DEEPSEEK_API_BASE_URL
    assert flash["model"] == "deepseek/deepseek-v4-flash"
    assert flash["extra_body"] == {"thinking": {"type": "disabled"}}
    assert pro["model"] == "deepseek/deepseek-v4-pro"
    assert pro["extra_body"] == {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
    }
    assert flash["max_tokens"] == 2048
    assert pro["max_tokens"] == 2048
    assert router_calls[0]["num_retries"] == 0
    assert {call["model"] for call in chat_calls} == {
        "journey-deepseek-deepseek-v4-flash",
        "journey-deepseek-deepseek-v4-pro",
    }
    assert structured_calls == [
        {"method": "function_calling", "include_raw": True},
        {"method": "json_mode", "include_raw": True},
    ]


def test_qwen_profile_uses_openai_compatible_litellm_route(monkeypatch) -> None:
    router_calls: list[dict] = []

    class FakeLiteLLMRouter:
        def __init__(self, **kwargs):
            router_calls.append(kwargs)

    monkeypatch.setattr("app.agent.model_router.LiteLLMRouter", FakeLiteLLMRouter)
    settings = replace(
        get_settings(),
        agent_provider="qwen",
        agent_api_key="test-qwen-placeholder",
        agent_api_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        agent_default_model="qwen3.6-flash",
        agent_model_map={"recommendation": "qwen3.7-plus"},
        agent_daily_budget_usd=1,
    )

    LangChainLiteLLMAdapter(settings)

    deployments = [item["litellm_params"] for item in router_calls[0]["model_list"]]
    assert {item["model"] for item in deployments} == {
        "openai/qwen3.6-flash",
        "openai/qwen3.7-plus",
    }
    assert all(
        item["api_base"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        for item in deployments
    )


def test_intent_router_regression_accuracy() -> None:
    cases = json.loads((EVALS / "intent_cases.json").read_text(encoding="utf-8"))
    correct = 0
    for case in cases:
        actual = [item.intent for item in deterministic_intent_plan(case["input"]).intents]
        correct += set(actual) == set(case["expected"])
    assert correct / len(cases) >= 0.90


def test_intent_router_prompt_distinguishes_profile_query_from_weight_write() -> None:
    assert ROUTER_PROMPT_VERSION == "intent-router-1.0.1"
    assert "查询已有的身高、体重、目标或个人资料属于 profile" in ROUTER_SYSTEM_PROMPT
    assert "提供明确体重数值" in ROUTER_SYSTEM_PROMPT


def test_rag_recall_at_three(seeded_knowledge) -> None:
    cases = json.loads((EVALS / "rag_cases.json").read_text(encoding="utf-8"))
    hits = 0
    with Session(engine) as db:
        for case in cases:
            slugs = {item.source_slug for item in retrieve(db, case["input"], limit=3)}
            hits += case["expected_slug"] in slugs
    assert hits / len(cases) >= 0.75


def test_model_timeout_returns_valid_structured_fallback() -> None:
    with Session(engine) as db:
        router = ModelRouter(
            db,
            settings=get_settings(),
            adapter=MockModelAdapter(failure="timeout"),
        )
        result = router.generate(
            "food_text_parse",
            FoodParsed,
            system_prompt="test",
            user_prompt="test",
            fallback_factory=lambda: FoodParsed(
                meal_type="other", name="fallback", energy_kcal=100
            ),
        )
    assert FoodParsed.model_validate(result.output).name == "fallback"
    assert result.fallback_used is True
    assert result.error_code == "model_timeout"
    assert result.estimated_cost_usd == 0
    assert result.retries == get_settings().agent_max_retries


def test_invalid_structured_output_returns_same_valid_fallback() -> None:
    with Session(engine) as db:
        router = ModelRouter(
            db,
            settings=get_settings(),
            adapter=MockModelAdapter(failure="invalid_json"),
        )
        result = router.generate(
            "food_text_parse",
            FoodParsed,
            system_prompt="test",
            user_prompt="test",
            fallback_factory=lambda: FoodParsed(
                meal_type="other", name="fallback", energy_kcal=100
            ),
        )
    assert FoodParsed.model_validate(result.output).name == "fallback"
    assert result.fallback_used is True
    assert result.error_code == "invalid_structured_output"


def test_provider_connection_error_returns_safe_fallback() -> None:
    with Session(engine) as db:
        router = ModelRouter(
            db,
            settings=replace(
                get_settings(),
                agent_provider="deepseek",
                agent_api_key="test-placeholder",
                agent_default_model="deepseek-v4-flash",
                agent_daily_budget_usd=1,
            ),
            adapter=UnavailableProviderAdapter(),
        )
        result = router.generate(
            "food_text_parse",
            FoodParsed,
            system_prompt="test",
            user_prompt="synthetic test",
            fallback_factory=lambda: FoodParsed(
                meal_type="other", name="fallback", energy_kcal=100
            ),
        )
    assert FoodParsed.model_validate(result.output).name == "fallback"
    assert result.fallback_used is True
    assert result.error_code == "provider_unavailable"
    assert result.estimated_cost_usd == 0


def test_model_specific_pricing_is_used_for_pro_capability() -> None:
    with Session(engine) as db:
        router = ModelRouter(
            db,
            settings=replace(
                get_settings(),
                agent_provider="deepseek",
                agent_api_key="test-placeholder",
                agent_default_model="deepseek-v4-flash",
                agent_model_map={"recommendation": "deepseek-v4-pro"},
                agent_model_pricing={
                    "deepseek-v4-flash": (0.14, 0.28),
                    "deepseek-v4-pro": (0.435, 0.87),
                },
                agent_daily_budget_usd=10,
            ),
            adapter=SuccessfulProviderAdapter(),
        )
        result = router.generate(
            "recommendation",
            FoodParsed,
            system_prompt="test",
            user_prompt="synthetic test",
            fallback_factory=lambda: FoodParsed(meal_type="other", name="test", energy_kcal=100),
        )

    assert result.model == "deepseek-v4-pro"
    assert result.estimated_cost_usd == 1.305


def test_rag_no_answer_does_not_generate_without_evidence(seeded_knowledge) -> None:
    with Session(engine) as db:
        result = run_knowledge(
            db,
            ModelRouter(db, adapter=FailIfCalledAdapter()),
            "法国首都是什么？",
        )
    assert "没有足够相关资料" in result.answer
    assert result.citations == []
    assert result.invocation.error_code == "insufficient_context"
    assert result.invocation.input_tokens == result.invocation.output_tokens == 0


def test_knowledge_ingestion_is_idempotent_and_keeps_chunk_ids(seeded_knowledge) -> None:
    from app.knowledge.ingest import ingest_builtin_knowledge

    with Session(engine) as db:
        before = list(db.scalars(select(KnowledgeChunk.id)).all())
        assert ingest_builtin_knowledge(db) == 0
        after = list(db.scalars(select(KnowledgeChunk.id)).all())
    assert before == after
