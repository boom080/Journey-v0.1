import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from app.agent.provider_profiles import AgentProvider, get_provider_profile

Environment = Literal["local", "test", "staging", "production"]
EXTERNAL_AGENT_PROVIDERS = {
    "openai",
    "deepseek",
    "qwen",
    "glm",
    "kimi",
    "openai_compatible",
}


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _boolean(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: Environment
    database_url: str
    secret_key: str
    cors_origins: tuple[str, ...]
    access_token_minutes: int
    refresh_token_days: int
    seed_test_account: bool
    test_account_email: str
    test_account_username: str
    test_account_password: str
    agent_provider: AgentProvider
    agent_api_key: str = field(repr=False)
    agent_v2_enabled: bool
    agent_v3_enabled: bool
    agent_api_base_url: str | None
    agent_default_model: str
    agent_model_map: dict[str, str]
    agent_model_pricing: dict[str, tuple[float, float]]
    agent_timeout_seconds: int
    agent_max_retries: int
    agent_max_output_tokens: int
    agent_daily_budget_usd: float
    agent_input_usd_per_million: float
    agent_output_usd_per_million: float
    food_image_analysis_enabled: bool
    food_image_provider: AgentProvider
    food_image_api_key: str = field(repr=False)
    food_image_api_base_url: str | None
    food_image_model: str
    food_image_input_usd_per_million: float
    food_image_output_usd_per_million: float
    food_image_daily_budget_usd: float
    food_image_external_upload_confirmed: bool
    food_image_max_bytes: int
    food_image_max_dimension: int
    life_inspiration_fetch_enabled: bool
    seed_builtin_knowledge: bool
    agent_external_enabled: bool = False
    agent_provider_policy_url: str = ""
    agent_provider_retention_notice: str = ""
    agent_data_retention_days: int = 7
    agent_provider_review_required: bool = True
    agent_provider_review_json: str = field(default="", repr=False)


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


def _non_negative_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be a number") from error
    if value < 0:
        raise RuntimeError(f"{name} must be non-negative")
    return value


def _model_map(name: str, default: dict[str, str] | None = None) -> dict[str, str]:
    raw_value = os.getenv(name, "{}").strip() or "{}"
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{name} must be valid JSON") from error
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(model, str) and model.strip()
        for key, model in value.items()
    ):
        raise RuntimeError(f"{name} must map capability names to model names")
    return {
        **(default or {}),
        **{key: model.strip() for key, model in value.items()},
    }


def _model_pricing(
    name: str,
    default: dict[str, tuple[float, float]] | None = None,
) -> dict[str, tuple[float, float]]:
    raw_value = os.getenv(name, "{}").strip() or "{}"
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{name} must be valid JSON") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{name} must map model names to input/output prices")
    parsed = dict(default or {})
    for model, prices in value.items():
        if not isinstance(model, str) or not model.strip() or not isinstance(prices, dict):
            raise RuntimeError(f"{name} must map model names to input/output prices")
        input_price = prices.get("input")
        output_price = prices.get("output")
        if (
            isinstance(input_price, bool)
            or isinstance(output_price, bool)
            or not isinstance(input_price, int | float)
            or not isinstance(output_price, int | float)
            or input_price <= 0
            or output_price <= 0
        ):
            raise RuntimeError(f"{name} prices must be positive numbers")
        parsed[model.strip()] = (float(input_price), float(output_price))
    return parsed


def _provider_value(
    provider: str,
    suffix: str,
    *,
    default: str = "",
    allow_legacy: bool = False,
) -> str:
    specific = os.getenv(f"{provider.upper()}_{suffix}")
    if specific is not None and specific.strip():
        return specific.strip()
    if allow_legacy:
        return os.getenv(f"AGENT_{suffix}", default).strip()
    return default


@lru_cache
def get_settings() -> Settings:
    environment = os.getenv("APP_ENV", "local").strip().lower()
    if environment not in {"local", "test", "staging", "production"}:
        raise RuntimeError("APP_ENV must be local, test, staging, or production")

    database_url = _required("DATABASE_URL")
    if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("DATABASE_URL must use PostgreSQL; SQLite is not supported")

    secret_key = _required("APP_SECRET_KEY")
    if len(secret_key) < 32:
        raise RuntimeError("APP_SECRET_KEY must contain at least 32 characters")
    if environment in {"staging", "production"} and secret_key.startswith("local-"):
        raise RuntimeError("Local development secrets cannot be used outside local/test")

    raw_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8081,http://localhost:19006,http://127.0.0.1:4173",
    )
    cors_origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())

    seed_test_account = _boolean("SEED_TEST_ACCOUNT")
    if environment in {"staging", "production"} and seed_test_account:
        raise RuntimeError("SEED_TEST_ACCOUNT cannot be enabled outside local/test")

    test_account_password = os.getenv("TEST_ACCOUNT_PASSWORD", "").strip()
    if seed_test_account and len(test_account_password.encode("utf-8")) < 10:
        raise RuntimeError("TEST_ACCOUNT_PASSWORD must contain at least 10 bytes")

    agent_provider = os.getenv("AGENT_PROVIDER", "mock").strip().lower()
    if agent_provider not in {"mock", *EXTERNAL_AGENT_PROVIDERS}:
        allowed = ", ".join(("mock", *sorted(EXTERNAL_AGENT_PROVIDERS)))
        raise RuntimeError(f"AGENT_PROVIDER must be one of: {allowed}")
    if environment in {"staging", "production"} and agent_provider == "mock":
        raise RuntimeError("AGENT_PROVIDER=mock cannot be enabled outside local/test")

    agent_api_key = ""
    agent_api_base_url = None
    agent_default_model = "journey-deterministic-v1"
    agent_model_map: dict[str, str] = {}
    agent_model_pricing: dict[str, tuple[float, float]] = {}
    if agent_provider != "mock":
        profile = get_provider_profile(agent_provider)
        allow_legacy = agent_provider in {"openai", "deepseek", "openai_compatible"}
        agent_api_key = _provider_value(
            agent_provider,
            "API_KEY",
            allow_legacy=allow_legacy,
        )
        agent_api_base_url = (
            _provider_value(
                agent_provider,
                "API_BASE_URL",
                default=profile.api_base_url or "",
                allow_legacy=allow_legacy,
            )
            or None
        )
        agent_default_model = _provider_value(
            agent_provider,
            "DEFAULT_MODEL",
            default=profile.default_model,
            allow_legacy=allow_legacy,
        )
        model_map_env = (
            "AGENT_MODEL_MAP_JSON"
            if allow_legacy and os.getenv(f"{agent_provider.upper()}_MODEL_MAP_JSON") is None
            else f"{agent_provider.upper()}_MODEL_MAP_JSON"
        )
        agent_model_map = _model_map(model_map_env, profile.capability_models)
        pricing_env = (
            "AGENT_MODEL_PRICING_JSON"
            if allow_legacy and os.getenv(f"{agent_provider.upper()}_MODEL_PRICING_JSON") is None
            else f"{agent_provider.upper()}_MODEL_PRICING_JSON"
        )
        agent_model_pricing = _model_pricing(pricing_env, profile.model_pricing)

    agent_daily_budget_usd = _non_negative_float("AGENT_DAILY_BUDGET_USD", 0.0)
    pricing_prefix = (
        "AGENT"
        if agent_provider in {"mock", "openai", "deepseek", "openai_compatible"}
        else agent_provider.upper()
    )
    agent_input_usd_per_million = _non_negative_float(
        f"{pricing_prefix}_INPUT_USD_PER_MILLION", 0.0
    )
    agent_output_usd_per_million = _non_negative_float(
        f"{pricing_prefix}_OUTPUT_USD_PER_MILLION", 0.0
    )
    if agent_provider != "mock":
        if not agent_api_key:
            profile = get_provider_profile(agent_provider)
            raise RuntimeError(
                f"{profile.api_key_env} is required when AGENT_PROVIDER={agent_provider}"
            )
        if not agent_default_model:
            raise RuntimeError("AGENT_DEFAULT_MODEL is required when AGENT_PROVIDER is not mock")
        if agent_daily_budget_usd <= 0:
            raise RuntimeError(
                "AGENT_DAILY_BUDGET_USD must be positive when external models are enabled"
            )
        if agent_provider == "openai_compatible" and not agent_api_base_url:
            raise RuntimeError(
                "AGENT_API_BASE_URL is required when AGENT_PROVIDER is openai_compatible"
            )
        configured_models = {agent_default_model, *agent_model_map.values()}
        missing_pricing = configured_models.difference(agent_model_pricing)
        if missing_pricing and (
            agent_input_usd_per_million <= 0 or agent_output_usd_per_million <= 0
        ):
            models = ", ".join(sorted(missing_pricing))
            raise RuntimeError(f"Model pricing is required before enabling: {models}")

    agent_external_enabled = _boolean("AGENT_EXTERNAL_ENABLED")
    agent_provider_policy_url = os.getenv("AGENT_PROVIDER_POLICY_URL", "").strip()
    agent_provider_retention_notice = os.getenv("AGENT_PROVIDER_RETENTION_NOTICE", "").strip()
    agent_data_retention_days = _positive_int("AGENT_DATA_RETENTION_DAYS", 7)
    agent_provider_review_required = _boolean("AGENT_PROVIDER_REVIEW_REQUIRED", True)
    if not agent_provider_review_required and environment != "local":
        raise RuntimeError("AGENT_PROVIDER_REVIEW_REQUIRED can only be false when APP_ENV=local")
    if agent_data_retention_days > 30:
        raise RuntimeError("AGENT_DATA_RETENTION_DAYS must not exceed 30")
    if agent_external_enabled and agent_provider != "mock":
        for address in (
            agent_provider_policy_url,
            *([agent_api_base_url] if agent_api_base_url else []),
        ):
            parsed = urlsplit(address or "")
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise RuntimeError(
                    "External Agent endpoint and policy URL must be credential-free HTTPS URLs"
                )
        if len(agent_provider_retention_notice) < 20:
            raise RuntimeError(
                "AGENT_PROVIDER_RETENTION_NOTICE must explain provider retention and deletion"
            )

    food_image_analysis_enabled = _boolean(
        "FOOD_IMAGE_ANALYSIS_ENABLED", environment in {"local", "test"}
    )
    food_image_provider = os.getenv("FOOD_IMAGE_PROVIDER", "mock").strip().lower()
    if food_image_provider not in {"mock", "openai", "qwen"}:
        raise RuntimeError("FOOD_IMAGE_PROVIDER must be one of: mock, openai, qwen")
    food_image_api_key = ""
    food_image_api_base_url = None
    food_image_model = "journey-food-image-mock-v1"
    food_image_input_usd_per_million = _non_negative_float("FOOD_IMAGE_INPUT_USD_PER_MILLION", 0.0)
    food_image_output_usd_per_million = _non_negative_float(
        "FOOD_IMAGE_OUTPUT_USD_PER_MILLION", 0.0
    )
    food_image_daily_budget_usd = _non_negative_float("FOOD_IMAGE_DAILY_BUDGET_USD", 0.0)
    food_image_external_upload_confirmed = _boolean("FOOD_IMAGE_EXTERNAL_UPLOAD_CONFIRMED")
    if food_image_analysis_enabled and food_image_provider != "mock":
        image_profile = get_provider_profile(food_image_provider)
        if not image_profile.vision_model:
            raise RuntimeError(f"{food_image_provider} is not approved for image input")
        food_image_api_key = os.getenv(image_profile.api_key_env, "").strip()
        food_image_api_base_url = os.getenv("FOOD_IMAGE_API_BASE_URL", "").strip() or (
            image_profile.api_base_url if food_image_provider == "openai" else None
        )
        food_image_model = os.getenv("FOOD_IMAGE_MODEL", "").strip() or image_profile.vision_model
        if not food_image_api_key:
            raise RuntimeError(
                f"{image_profile.api_key_env} is required when "
                f"FOOD_IMAGE_PROVIDER={food_image_provider}"
            )
        if not food_image_external_upload_confirmed:
            raise RuntimeError(
                "FOOD_IMAGE_EXTERNAL_UPLOAD_CONFIRMED must be true before external image upload"
            )
        if food_image_provider == "qwen" and not food_image_api_base_url:
            raise RuntimeError(
                "FOOD_IMAGE_API_BASE_URL must use the confirmed regional Qwen endpoint"
            )
        if food_image_daily_budget_usd <= 0:
            raise RuntimeError(
                "FOOD_IMAGE_DAILY_BUDGET_USD must be positive for external image analysis"
            )
        if food_image_input_usd_per_million <= 0 or food_image_output_usd_per_million <= 0:
            raise RuntimeError("Food image model pricing is required before external activation")

    return Settings(
        environment=environment,  # type: ignore[arg-type]
        database_url=database_url,
        secret_key=secret_key,
        cors_origins=cors_origins,
        access_token_minutes=_positive_int("ACCESS_TOKEN_MINUTES", 15),
        refresh_token_days=_positive_int("REFRESH_TOKEN_DAYS", 30),
        seed_test_account=seed_test_account,
        test_account_email=os.getenv("TEST_ACCOUNT_EMAIL", "demo@journey.local").strip(),
        test_account_username=os.getenv("TEST_ACCOUNT_USERNAME", "journey_demo").strip(),
        test_account_password=test_account_password,
        agent_provider=agent_provider,  # type: ignore[arg-type]
        agent_api_key=agent_api_key,
        agent_v2_enabled=_boolean("AGENT_V2_ENABLED", True),
        agent_v3_enabled=_boolean("AGENT_V3_ENABLED", True),
        agent_api_base_url=agent_api_base_url,
        agent_default_model=agent_default_model,
        agent_model_map=agent_model_map,
        agent_model_pricing=agent_model_pricing,
        agent_timeout_seconds=_positive_int("AGENT_TIMEOUT_SECONDS", 30),
        agent_max_retries=_positive_int("AGENT_MAX_RETRIES", 1),
        agent_max_output_tokens=_positive_int("AGENT_MAX_OUTPUT_TOKENS", 2048),
        agent_daily_budget_usd=agent_daily_budget_usd,
        agent_input_usd_per_million=agent_input_usd_per_million,
        agent_output_usd_per_million=agent_output_usd_per_million,
        food_image_analysis_enabled=food_image_analysis_enabled,
        food_image_provider=food_image_provider,  # type: ignore[arg-type]
        food_image_api_key=food_image_api_key,
        food_image_api_base_url=food_image_api_base_url,
        food_image_model=food_image_model,
        food_image_input_usd_per_million=food_image_input_usd_per_million,
        food_image_output_usd_per_million=food_image_output_usd_per_million,
        food_image_daily_budget_usd=food_image_daily_budget_usd,
        food_image_external_upload_confirmed=food_image_external_upload_confirmed,
        food_image_max_bytes=_positive_int("FOOD_IMAGE_MAX_BYTES", 5 * 1024 * 1024),
        food_image_max_dimension=_positive_int("FOOD_IMAGE_MAX_DIMENSION", 4096),
        life_inspiration_fetch_enabled=_boolean(
            "LIFE_INSPIRATION_FETCH_ENABLED", environment in {"local", "test"}
        ),
        seed_builtin_knowledge=_boolean("SEED_BUILTIN_KNOWLEDGE", environment in {"local", "test"}),
        agent_external_enabled=agent_external_enabled,
        agent_provider_policy_url=agent_provider_policy_url,
        agent_provider_retention_notice=agent_provider_retention_notice,
        agent_data_retention_days=agent_data_retention_days,
        agent_provider_review_required=agent_provider_review_required,
        agent_provider_review_json=os.getenv("AGENT_PROVIDER_REVIEW_JSON", ""),
    )
