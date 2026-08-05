from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

AgentProvider = Literal[
    "mock",
    "openai",
    "deepseek",
    "qwen",
    "glm",
    "kimi",
    "openai_compatible",
]


@dataclass(frozen=True)
class ProviderProfile:
    name: AgentProvider
    api_key_env: str
    api_base_url: str | None
    default_model: str
    litellm_provider: str
    vision_model: str | None = None
    capability_models: dict[str, str] = field(default_factory=dict)
    model_pricing: dict[str, tuple[float, float]] = field(default_factory=dict)


PROVIDER_PROFILES = MappingProxyType(
    {
        "openai": ProviderProfile(
            name="openai",
            api_key_env="OPENAI_API_KEY",
            api_base_url=None,
            default_model="gpt-5-mini",
            litellm_provider="openai",
            vision_model="gpt-5-mini",
        ),
        "deepseek": ProviderProfile(
            name="deepseek",
            api_key_env="DEEPSEEK_API_KEY",
            api_base_url="https://api.deepseek.com",
            default_model="deepseek-v4-flash",
            litellm_provider="deepseek",
            capability_models={
                "recommendation": "deepseek-v4-pro",
                "weekly_summary": "deepseek-v4-pro",
            },
            model_pricing={
                "deepseek-v4-flash": (0.14, 0.28),
                "deepseek-v4-pro": (0.435, 0.87),
            },
        ),
        "qwen": ProviderProfile(
            name="qwen",
            api_key_env="QWEN_API_KEY",
            api_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            default_model="qwen3.6-flash",
            litellm_provider="openai",
            vision_model="qwen3.7-flash",
            capability_models={
                "recommendation": "qwen3.7-plus",
                "weekly_summary": "qwen3.7-plus",
            },
        ),
        "glm": ProviderProfile(
            name="glm",
            api_key_env="GLM_API_KEY",
            api_base_url="https://open.bigmodel.cn/api/paas/v4",
            default_model="glm-5.2",
            litellm_provider="openai",
        ),
        "kimi": ProviderProfile(
            name="kimi",
            api_key_env="KIMI_API_KEY",
            api_base_url="https://api.moonshot.cn/v1",
            default_model="kimi-k2.6",
            litellm_provider="openai",
        ),
        "openai_compatible": ProviderProfile(
            name="openai_compatible",
            api_key_env="OPENAI_COMPATIBLE_API_KEY",
            api_base_url=None,
            default_model="",
            litellm_provider="openai",
        ),
    }
)


def get_provider_profile(provider: str) -> ProviderProfile:
    if provider == "mock":
        raise ValueError("mock does not use an external provider profile")
    try:
        return PROVIDER_PROFILES[provider]
    except KeyError as error:
        raise ValueError(f"unsupported provider profile: {provider}") from error


def litellm_model_name(profile: ProviderProfile, model: str) -> str:
    if "/" in model:
        return model
    return f"{profile.litellm_provider}/{model}"
