import pytest

from app.core.settings import get_settings


def test_secret_is_required(monkeypatch) -> None:
    monkeypatch.delenv("APP_SECRET_KEY")
    get_settings.cache_clear()

    try:
        with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_provider_review_can_only_be_optional_for_local_personal_use(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("AGENT_PROVIDER_REVIEW_REQUIRED", "false")
    get_settings.cache_clear()
    try:
        assert get_settings().agent_provider_review_required is False
    finally:
        get_settings.cache_clear()

    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="only be false when APP_ENV=local"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_sqlite_database_url_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///journey.db")
    get_settings.cache_clear()

    try:
        with pytest.raises(RuntimeError, match="PostgreSQL"):
            get_settings()
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_test_account_seed_is_rejected_outside_local_test(monkeypatch, environment: str) -> None:
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setenv("APP_SECRET_KEY", "production-secret-at-least-32-characters")
    monkeypatch.setenv("SEED_TEST_ACCOUNT", "true")
    get_settings.cache_clear()

    try:
        with pytest.raises(RuntimeError, match="cannot be enabled outside local/test"):
            get_settings()
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_mock_agent_is_rejected_outside_local_test(monkeypatch, environment: str) -> None:
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setenv("APP_SECRET_KEY", "production-secret-at-least-32-characters")
    monkeypatch.setenv("SEED_TEST_ACCOUNT", "false")
    monkeypatch.setenv("AGENT_PROVIDER", "mock")
    get_settings.cache_clear()

    try:
        with pytest.raises(RuntimeError, match="mock cannot be enabled outside local/test"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_enabled_test_account_requires_nontrivial_password(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SEED_TEST_ACCOUNT", "true")
    monkeypatch.setenv("TEST_ACCOUNT_PASSWORD", "short")
    get_settings.cache_clear()

    try:
        with pytest.raises(RuntimeError, match="at least 10 bytes"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_external_agent_requires_key_and_positive_budget(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_API_KEY", "")
    monkeypatch.setenv("AGENT_DAILY_BUDGET_USD", "0")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            get_settings()
        monkeypatch.setenv("AGENT_API_KEY", "test-placeholder")
        get_settings.cache_clear()
        with pytest.raises(RuntimeError, match="AGENT_DAILY_BUDGET_USD"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_openai_compatible_provider_requires_base_url(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AGENT_API_KEY", "test-placeholder")
    monkeypatch.setenv("AGENT_DEFAULT_MODEL", "test-compatible-model")
    monkeypatch.setenv("AGENT_DAILY_BUDGET_USD", "1")
    monkeypatch.setenv("AGENT_API_BASE_URL", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="AGENT_API_BASE_URL"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_qwen_profile_requires_its_own_key_and_ignores_legacy_key(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "qwen")
    monkeypatch.setenv("AGENT_API_KEY", "must-not-be-forwarded-to-qwen")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_DAILY_BUDGET_USD", "1")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="QWEN_API_KEY"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_provider_profile_switch_selects_qwen_defaults(monkeypatch) -> None:
    api_key = "test-placeholder-qwen-key"
    monkeypatch.setenv("AGENT_PROVIDER", "qwen")
    monkeypatch.setenv("QWEN_API_KEY", api_key)
    monkeypatch.setenv("AGENT_DAILY_BUDGET_USD", "1")
    monkeypatch.delenv("QWEN_DEFAULT_MODEL", raising=False)
    monkeypatch.delenv("QWEN_MODEL_MAP_JSON", raising=False)
    monkeypatch.setenv(
        "QWEN_MODEL_PRICING_JSON",
        '{"qwen3.6-flash":{"input":0.1,"output":0.2},"qwen3.7-plus":{"input":0.3,"output":0.6}}',
    )
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.agent_default_model == "qwen3.6-flash"
        assert settings.agent_model_map["recommendation"] == "qwen3.7-plus"
        assert settings.agent_model_pricing["qwen3.7-plus"] == (0.3, 0.6)
        assert settings.agent_api_base_url == ("https://dashscope.aliyuncs.com/compatible-mode/v1")
        assert api_key not in repr(settings)
    finally:
        get_settings.cache_clear()


def test_unpriced_future_profile_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "kimi")
    monkeypatch.setenv("KIMI_API_KEY", "test-placeholder-kimi-key")
    monkeypatch.setenv("AGENT_DAILY_BUDGET_USD", "1")
    monkeypatch.delenv("KIMI_MODEL_PRICING_JSON", raising=False)
    monkeypatch.delenv("KIMI_INPUT_USD_PER_MILLION", raising=False)
    monkeypatch.delenv("KIMI_OUTPUT_USD_PER_MILLION", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="Model pricing"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_deepseek_v4_configuration_maps_models_and_redacts_key(monkeypatch) -> None:
    api_key = "test-placeholder-deepseek-key"
    monkeypatch.setenv("AGENT_PROVIDER", "deepseek")
    monkeypatch.setenv("AGENT_API_KEY", api_key)
    monkeypatch.setenv("AGENT_DEFAULT_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv(
        "AGENT_MODEL_MAP_JSON",
        '{"recommendation":"deepseek-v4-pro","weekly_summary":"deepseek-v4-pro"}',
    )
    monkeypatch.setenv("AGENT_DAILY_BUDGET_USD", "0.10")
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.agent_provider == "deepseek"
        assert settings.agent_default_model == "deepseek-v4-flash"
        assert settings.agent_model_map["recommendation"] == "deepseek-v4-pro"
        assert settings.agent_model_pricing["deepseek-v4-pro"] == (0.435, 0.87)
        assert settings.agent_max_output_tokens == 2048
        assert api_key not in repr(settings)
    finally:
        get_settings.cache_clear()


def test_food_image_defaults_to_zero_cost_mock() -> None:
    settings = get_settings()
    assert settings.food_image_analysis_enabled is True
    assert settings.food_image_provider == "mock"
    assert settings.food_image_model == "journey-food-image-mock-v1"
    assert settings.food_image_daily_budget_usd == 0
    assert settings.food_image_external_upload_confirmed is False
    assert "food_image_api_key" not in repr(settings)


def test_food_image_rejects_text_only_or_unapproved_provider(monkeypatch) -> None:
    monkeypatch.setenv("FOOD_IMAGE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("FOOD_IMAGE_PROVIDER", "deepseek")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="FOOD_IMAGE_PROVIDER"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_external_food_image_requires_explicit_upload_confirmation(monkeypatch) -> None:
    monkeypatch.setenv("FOOD_IMAGE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("FOOD_IMAGE_PROVIDER", "qwen")
    monkeypatch.setenv("QWEN_API_KEY", "test-qwen-image-key")
    monkeypatch.setenv(
        "FOOD_IMAGE_API_BASE_URL",
        "https://test-workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
    )
    monkeypatch.setenv("FOOD_IMAGE_DAILY_BUDGET_USD", "1")
    monkeypatch.setenv("FOOD_IMAGE_INPUT_USD_PER_MILLION", "1")
    monkeypatch.setenv("FOOD_IMAGE_OUTPUT_USD_PER_MILLION", "1")
    monkeypatch.setenv("FOOD_IMAGE_EXTERNAL_UPLOAD_CONFIRMED", "false")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="EXTERNAL_UPLOAD_CONFIRMED"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_qwen_food_image_requires_confirmed_regional_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("FOOD_IMAGE_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("FOOD_IMAGE_PROVIDER", "qwen")
    monkeypatch.setenv("QWEN_API_KEY", "test-qwen-image-key")
    monkeypatch.setenv("FOOD_IMAGE_API_BASE_URL", "")
    monkeypatch.setenv("FOOD_IMAGE_DAILY_BUDGET_USD", "1")
    monkeypatch.setenv("FOOD_IMAGE_INPUT_USD_PER_MILLION", "1")
    monkeypatch.setenv("FOOD_IMAGE_OUTPUT_USD_PER_MILLION", "1")
    monkeypatch.setenv("FOOD_IMAGE_EXTERNAL_UPLOAD_CONFIRMED", "true")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="regional Qwen endpoint"):
            get_settings()
    finally:
        get_settings.cache_clear()
