import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv()

PROVIDER_ENV_PREFIX = {
    "qwen": "QWEN",
    "deepseek": "DEEPSEEK",
    "openai": "OPENAI",
    "self_hosted": "SELF_HOSTED",
}


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class AIProviderConfig:
    provider: str
    api_key: str
    base_url: str
    model: str


@dataclass(frozen=True)
class AISettings:
    enabled: bool
    provider: str
    timeout_seconds: int
    capability_flags: Dict[str, bool]

    def is_capability_enabled(self, capability: str) -> bool:
        return self.enabled and bool(self.capability_flags.get(capability, False))

    def get_provider_config(self) -> Optional[AIProviderConfig]:
        prefix = PROVIDER_ENV_PREFIX.get(self.provider)
        if not prefix:
            return None

        api_key = os.getenv(f"{prefix}_API_KEY", "").strip()
        base_url = os.getenv(f"{prefix}_BASE_URL", "").strip().rstrip("/")
        model = os.getenv(f"{prefix}_MODEL", "").strip()

        if not api_key or not base_url or not model:
            return None

        return AIProviderConfig(
            provider=self.provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )


@lru_cache()
def get_ai_settings() -> AISettings:
    capability_flags = {
        "food_text_estimate": _env_flag("AI_FOOD_TEXT_ENABLED", True),
        "activity_text_estimate": _env_flag("AI_ACTIVITY_TEXT_ENABLED", True),
        "home_suggestion": _env_flag("AI_HOME_SUGGESTION_ENABLED", True),
        "food_image_analysis": _env_flag("AI_FOOD_IMAGE_ENABLED", False),
        "activity_ocr_analysis": _env_flag("AI_ACTIVITY_OCR_ENABLED", False),
        "pdf_parse": _env_flag("AI_PDF_ENABLED", False),
        "rag_knowledge_query": _env_flag("AI_RAG_ENABLED", False),
    }

    return AISettings(
        enabled=_env_flag("AI_ENABLED", True),
        provider=os.getenv("AI_PROVIDER", "qwen").strip().lower() or "qwen",
        timeout_seconds=_env_int("AI_TIMEOUT_SECONDS", 20),
        capability_flags=capability_flags,
    )
