import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLMRouter
from langsmith import tracing_context
from litellm import Router as LiteLLMRouter
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)
from opentelemetry import trace
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.provider_profiles import get_provider_profile, litellm_model_name
from app.core.privacy import prepare_model_prompt, redact_payload, redact_text
from app.core.settings import Settings, get_settings
from app.models.agent import AgentRun
from app.models.agent_privacy import AgentDeletedCost
from app.models.profile import Profile
from app.models.user import Identity
from app.services.agent_privacy import require_external_consent

PROMPT_VERSION = "journey-agent-2.0.0"
SCHEMA_VERSION = "journey-agent-schema-2"
KNOWLEDGE_VERSION = "journey-core-1.0.0"
DEEPSEEK_API_BASE_URL = get_provider_profile("deepseek").api_base_url
tracer = trace.get_tracer("journey.agent")
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True)
class ModelInvocation:
    output: BaseModel
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    retries: int
    latency_ms: int
    estimated_cost_usd: float
    fallback_used: bool
    error_code: str | None = None


class ModelAdapter:
    provider: str

    def invoke_structured(
        self,
        *,
        model: str,
        schema: type[OutputT],
        system_prompt: str,
        user_prompt: str,
        fallback_factory: Callable[[], OutputT],
    ) -> tuple[OutputT, int, int]:
        raise NotImplementedError


class MockModelAdapter(ModelAdapter):
    provider = "mock"

    def __init__(self, failure: str | None = None):
        self.failure = failure

    def invoke_structured(
        self,
        *,
        model: str,
        schema: type[OutputT],
        system_prompt: str,
        user_prompt: str,
        fallback_factory: Callable[[], OutputT],
    ) -> tuple[OutputT, int, int]:
        if self.failure == "timeout":
            raise TimeoutError("mock model timeout")
        if self.failure == "invalid_json":
            raise ValueError("mock invalid structured output")
        output = schema.model_validate(fallback_factory())
        return (
            output,
            _approximate_tokens(system_prompt + user_prompt),
            _approximate_tokens(output.model_dump_json()),
        )


class LangChainLiteLLMAdapter(ModelAdapter):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.agent_provider
        self.profile = get_provider_profile(self.provider)
        self.router = LiteLLMRouter(
            model_list=self._model_list(),
            num_retries=0,
            max_fallbacks=0,
            timeout=settings.agent_timeout_seconds,
            cache_responses=False,
            disable_cooldowns=True,
        )
        self._chat_models: dict[str, ChatLiteLLMRouter] = {}

    def _route_name(self, model: str) -> str:
        return f"journey-{self.provider}-{model}"

    def _extra_body(self, model: str) -> dict | None:
        if self.provider != "deepseek":
            return None
        if model == "deepseek-v4-pro":
            return {
                "thinking": {"type": "enabled"},
                "reasoning_effort": "high",
            }
        return {"thinking": {"type": "disabled"}}

    def _model_list(self) -> list[dict]:
        models = {
            self.settings.agent_default_model,
            *self.settings.agent_model_map.values(),
        }
        deployments = []
        for model in sorted(models):
            params = {
                "model": litellm_model_name(self.profile, model),
                "api_key": self.settings.agent_api_key,
                "timeout": self.settings.agent_timeout_seconds,
                "max_retries": 0,
                "max_tokens": self.settings.agent_max_output_tokens,
                "temperature": 0,
            }
            api_base_url = self.settings.agent_api_base_url or self.profile.api_base_url
            if api_base_url:
                params["api_base"] = api_base_url
            if extra_body := self._extra_body(model):
                params["extra_body"] = extra_body
            deployments.append(
                {
                    "model_name": self._route_name(model),
                    "litellm_params": params,
                }
            )
        return deployments

    def _chat_for(self, model: str) -> ChatLiteLLMRouter:
        if model not in self._chat_models:
            self._chat_models[model] = ChatLiteLLMRouter(
                router=self.router,
                model=self._route_name(model),
                temperature=0,
                request_timeout=self.settings.agent_timeout_seconds,
                max_retries=0,
            )
        return self._chat_models[model]

    def _structured_output_method(self, model: str) -> str:
        if self.provider == "deepseek" and model == "deepseek-v4-pro":
            return "json_mode"
        return "function_calling"

    def invoke_structured(
        self,
        *,
        model: str,
        schema: type[OutputT],
        system_prompt: str,
        user_prompt: str,
        fallback_factory: Callable[[], OutputT],
    ) -> tuple[OutputT, int, int]:
        chat = self._chat_for(model)
        method = self._structured_output_method(model)
        if method == "json_mode":
            schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
            system_prompt = (
                f"{system_prompt}\n"
                "仅输出一个符合以下 JSON Schema 的 JSON 对象，不要添加 Markdown 标记："
                f"{schema_json}"
            )
        # Opt out even if a host-level LangSmith tracing environment is present.
        with tracing_context(enabled=False):
            result = chat.with_structured_output(schema, method=method, include_raw=True).invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
        parsed = result.get("parsed") if isinstance(result, dict) else None
        if parsed is None:
            raise ValueError("provider returned invalid structured output")
        validated = schema.model_validate(parsed)
        raw = result.get("raw") if isinstance(result, dict) else None
        usage = getattr(raw, "usage_metadata", None) or {}
        return (
            validated,
            int(usage.get("input_tokens") or _approximate_tokens(system_prompt + user_prompt)),
            int(usage.get("output_tokens") or _approximate_tokens(validated.model_dump_json())),
        )


def _approximate_tokens(text: str) -> int:
    return max(1, (len(text) + 2) // 3)


def _safe_error_code(error: Exception | None) -> str:
    if isinstance(error, TimeoutError | APITimeoutError):
        return "model_timeout"
    if isinstance(error, AuthenticationError):
        return "provider_auth_error"
    if isinstance(error, RateLimitError):
        return "provider_rate_limited"
    if isinstance(error, APIConnectionError):
        return "provider_unavailable"
    if isinstance(error, APIStatusError):
        return f"provider_http_{error.status_code}"
    if isinstance(error, ValueError):
        return "invalid_structured_output"
    if isinstance(error, RuntimeError):
        return (
            "agent_daily_budget_exceeded"
            if str(error) == "agent_daily_budget_exceeded"
            else "model_unavailable"
        )
    return "model_unavailable"


class ModelRouter:
    def __init__(
        self,
        db: Session,
        *,
        settings: Settings | None = None,
        adapter: ModelAdapter | None = None,
        user_id: uuid.UUID | None = None,
    ):
        self.db = db
        self.settings = settings or get_settings()
        self.user_id = user_id
        # No real SDK/client construction before account-scoped consent passes.
        self.adapter = adapter or (
            MockModelAdapter() if self.settings.agent_provider == "mock" else None
        )

    @property
    def provider(self) -> str:
        return self.adapter.provider if self.adapter is not None else self.settings.agent_provider

    def bind_user(self, user_id: uuid.UUID) -> None:
        if self.user_id is not None and self.user_id != user_id:
            raise RuntimeError("model_router_user_mismatch")
        self.user_id = user_id

    def authorize(self) -> None:
        require_external_consent(
            self.db, self.user_id, replace(self.settings, agent_provider=self.provider)
        )

    def private_values(self) -> tuple[str, ...]:
        if self.user_id is None:
            return ()
        values = list(
            self.db.scalars(select(Identity.display_value).where(Identity.user_id == self.user_id))
        )
        profile = self.db.scalar(select(Profile).where(Profile.user_id == self.user_id))
        if profile:
            values.extend(
                [profile.display_name, profile.birth_date.isoformat() if profile.birth_date else ""]
            )
        return tuple(value for value in values if value)

    def model_for(self, capability: str) -> str:
        return self.settings.agent_model_map.get(capability, self.settings.agent_default_model)

    def _check_budget(self) -> None:
        if self.provider == "mock":
            return
        spent = self.db.scalar(
            select(func.coalesce(func.sum(AgentRun.estimated_cost_usd), 0)).where(
                AgentRun.created_at >= func.current_date()
            )
        )
        deleted_cost = self.db.scalar(
            select(AgentDeletedCost.cost_usd).where(AgentDeletedCost.day == func.current_date())
        )
        if Decimal(str(spent or 0)) + Decimal(str(deleted_cost or 0)) >= Decimal(
            str(self.settings.agent_daily_budget_usd)
        ):
            raise RuntimeError("agent_daily_budget_exceeded")

    def generate(
        self,
        capability: str,
        schema: type[OutputT],
        *,
        system_prompt: str,
        user_prompt: str,
        fallback_factory: Callable[[], OutputT],
        max_retries: int | None = None,
    ) -> ModelInvocation:
        self.authorize()
        model = self.model_for(capability)
        started = time.perf_counter()
        configured_retries = (
            self.settings.agent_max_retries if max_retries is None else max(0, max_retries)
        )
        attempts = configured_retries + 1
        last_error: Exception | None = None
        private_values = self.private_values()
        with tracer.start_as_current_span(
            "agent.model", record_exception=False, set_status_on_exception=False
        ) as span:
            span.set_attribute("journey.agent.capability", capability)
            span.set_attribute("journey.agent.provider", self.provider)
            span.set_attribute("journey.agent.model", model)
            for attempt in range(attempts):
                self.authorize()
                try:
                    self._check_budget()
                    outbound_prompt = (
                        prepare_model_prompt(capability, user_prompt, private_values)
                        if self.provider != "mock"
                        else user_prompt
                    )
                    if self.adapter is None:
                        self.adapter = LangChainLiteLLMAdapter(self.settings)
                    output, input_tokens, output_tokens = self.adapter.invoke_structured(
                        model=model,
                        schema=schema,
                        system_prompt=redact_text(system_prompt, private_values),
                        user_prompt=outbound_prompt,
                        fallback_factory=fallback_factory,
                    )
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    input_rate, output_rate = self.settings.agent_model_pricing.get(
                        model,
                        (
                            self.settings.agent_input_usd_per_million,
                            self.settings.agent_output_usd_per_million,
                        ),
                    )
                    cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
                    return ModelInvocation(
                        output=schema.model_validate(
                            redact_payload(output.model_dump(mode="json"), private_values)
                        ),
                        provider=self.provider,
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        retries=attempt,
                        latency_ms=latency_ms,
                        estimated_cost_usd=round(cost, 8),
                        fallback_used=self.provider == "mock",
                    )
                except (TimeoutError, ValueError, RuntimeError, OpenAIError) as error:
                    last_error = error
            fallback = schema.model_validate(fallback_factory())
            fallback = schema.model_validate(
                redact_payload(fallback.model_dump(mode="json"), private_values)
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            error_code = _safe_error_code(last_error)
            span.set_attribute("journey.agent.fallback", True)
            span.set_attribute("journey.agent.error_code", error_code[:80])
            return ModelInvocation(
                output=fallback,
                provider=self.provider,
                model=model,
                input_tokens=_approximate_tokens(system_prompt + user_prompt),
                output_tokens=_approximate_tokens(fallback.model_dump_json()),
                retries=max(0, attempts - 1),
                latency_ms=latency_ms,
                estimated_cost_usd=0,
                fallback_used=True,
                error_code=error_code[:80],
            )
