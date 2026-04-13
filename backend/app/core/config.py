import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

PROVIDER_ENV_PREFIX = {
    "qwen": "QWEN",
    "deepseek": "DEEPSEEK",
    "openai": "OPENAI",
    "self_hosted": "SELF_HOSTED",
}

TEXT_CAPABILITIES = {
    "food_text_estimate",
    "activity_text_estimate",
    "home_suggestion",
    "pdf_parse",
    "rag_knowledge_query",
}

VISION_CAPABILITIES = {
    "food_image_analysis",
    "activity_ocr_analysis",
}

DEFAULT_TEXT_FALLBACKS = {
    "qwen": ["qwen3-max", "qwen-plus", "qwen-turbo"],
    "deepseek": ["deepseek-chat"],
    "openai": ["gpt-4.1-mini"],
    "self_hosted": [],
}

DEFAULT_VISION_FALLBACKS = {
    "qwen": ["qwen-vl-max", "qwen-vl-plus"],
    "openai": ["gpt-4.1-mini"],
    "deepseek": [],
    "self_hosted": [],
}

CAPABILITY_CANDIDATE_ENV = {
    "food_text_estimate": "AI_FOOD_TEXT_MODEL_CANDIDATES",
    "activity_text_estimate": "AI_ACTIVITY_TEXT_MODEL_CANDIDATES",
    "home_suggestion": "AI_HOME_SUGGESTION_MODEL_CANDIDATES",
    "food_image_analysis": "AI_FOOD_IMAGE_MODEL_CANDIDATES",
    "activity_ocr_analysis": "AI_ACTIVITY_OCR_MODEL_CANDIDATES",
    "pdf_parse": "AI_PDF_MODEL_CANDIDATES",
    "rag_knowledge_query": "AI_RAG_MODEL_CANDIDATES",
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


@dataclass(frozen=True)
class AIModelCandidate:
    provider: str
    model: str
    supports_vision: bool = False

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass(frozen=True)
class AISettings:
    enabled: bool
    provider: str
    timeout_seconds: int
    capability_flags: Dict[str, bool]
    provider_configs: Dict[str, AIProviderConfig]
    capability_model_candidates: Dict[str, List[AIModelCandidate]]

    def is_capability_enabled(self, capability: str) -> bool:
        return self.enabled and bool(self.capability_flags.get(capability, False))

    def get_provider_config(self, provider: str) -> Optional[AIProviderConfig]:
        return self.provider_configs.get(provider)

    def get_candidates_for_capability(self, capability: str) -> List[AIModelCandidate]:
        return list(self.capability_model_candidates.get(capability, []))


def _read_provider_config(provider: str) -> Optional[AIProviderConfig]:
    prefix = PROVIDER_ENV_PREFIX.get(provider)
    if not prefix:
        return None

    api_key = os.getenv(f"{prefix}_API_KEY", "").strip()
    base_url = os.getenv(f"{prefix}_BASE_URL", "").strip().rstrip("/")

    if not api_key or not base_url:
        return None

    return AIProviderConfig(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
    )


def _read_legacy_model(provider: str) -> str:
    prefix = PROVIDER_ENV_PREFIX.get(provider)
    if not prefix:
        return ""

    return os.getenv(f"{prefix}_MODEL", "").strip()


def _dedupe_candidates(candidates: List[AIModelCandidate]) -> List[AIModelCandidate]:
    seen = set()
    output: List[AIModelCandidate] = []

    for candidate in candidates:
        key = (candidate.provider, candidate.model, candidate.supports_vision)
        if candidate.model and key not in seen:
            seen.add(key)
            output.append(candidate)

    return output


def _parse_candidate_list(raw_value: str, default_provider: str, supports_vision: bool) -> List[AIModelCandidate]:
    candidates: List[AIModelCandidate] = []

    for chunk in raw_value.split(","):
        entry = chunk.strip()
        if not entry:
            continue

        if ":" in entry:
            provider, model = entry.split(":", 1)
            provider_name = provider.strip().lower()
            model_name = model.strip()
        else:
            provider_name = default_provider
            model_name = entry

        if provider_name and model_name:
            candidates.append(
                AIModelCandidate(
                    provider=provider_name,
                    model=model_name,
                    supports_vision=supports_vision,
                )
            )

    return _dedupe_candidates(candidates)


def _build_default_candidates(default_provider: str, supports_vision: bool) -> List[AIModelCandidate]:
    legacy_model = _read_legacy_model(default_provider)
    fallback_models = DEFAULT_VISION_FALLBACKS if supports_vision else DEFAULT_TEXT_FALLBACKS
    models = []

    if legacy_model:
        models.append(legacy_model)

    models.extend(fallback_models.get(default_provider, []))

    return _dedupe_candidates(
        [
            AIModelCandidate(
                provider=default_provider,
                model=model_name,
                supports_vision=supports_vision,
            )
            for model_name in models
        ]
    )


def _resolve_capability_candidates(capability: str, default_provider: str) -> List[AIModelCandidate]:
    env_name = CAPABILITY_CANDIDATE_ENV.get(capability, "")
    raw_value = os.getenv(env_name, "").strip() if env_name else ""
    supports_vision = capability in VISION_CAPABILITIES

    if raw_value:
        return _parse_candidate_list(raw_value, default_provider, supports_vision)

    fallback_env_name = "AI_VISION_MODEL_CANDIDATES" if supports_vision else "AI_TEXT_MODEL_CANDIDATES"
    fallback_raw_value = os.getenv(fallback_env_name, "").strip()
    if fallback_raw_value:
        return _parse_candidate_list(fallback_raw_value, default_provider, supports_vision)

    return _build_default_candidates(default_provider, supports_vision)


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

    default_provider = os.getenv("AI_PROVIDER", "qwen").strip().lower() or "qwen"
    provider_configs = {
        provider: config
        for provider in PROVIDER_ENV_PREFIX
        if (config := _read_provider_config(provider)) is not None
    }

    capability_model_candidates = {
        capability: _resolve_capability_candidates(capability, default_provider)
        for capability in [*TEXT_CAPABILITIES, *VISION_CAPABILITIES]
    }

    return AISettings(
        enabled=_env_flag("AI_ENABLED", True),
        provider=default_provider,
        timeout_seconds=_env_int("AI_TIMEOUT_SECONDS", 20),
        capability_flags=capability_flags,
        provider_configs=provider_configs,
        capability_model_candidates=capability_model_candidates,
    )
