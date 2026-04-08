import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import AIProviderConfig, get_ai_settings

logger = logging.getLogger("journey.ai.client")


class AIClientError(Exception):
    pass


class BaseAIClient(ABC):
    def __init__(self, provider_name: str = "", model_name: str = ""):
        self.provider_name = provider_name
        self.model_name = model_name

    def is_available(self) -> bool:
        return True

    @abstractmethod
    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        trace_id: str = "",
    ) -> Dict[str, Any]:
        raise NotImplementedError


class DisabledAIClient(BaseAIClient):
    def __init__(self):
        super().__init__(provider_name="disabled", model_name="")

    def is_available(self) -> bool:
        return False

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        trace_id: str = "",
    ) -> Dict[str, Any]:
        raise AIClientError("AI provider is not configured")


class OpenAICompatibleAIClient(BaseAIClient):
    def __init__(self, config: AIProviderConfig, timeout_seconds: int):
        super().__init__(provider_name=config.provider, model_name=config.model)
        self.api_key = config.api_key
        self.base_url = config.base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        trace_id: str = "",
    ) -> Dict[str, Any]:
        logger.info(
            "ai_gateway_request trace_id=%s provider=%s model=%s base_url=%s",
            trace_id or "-",
            self.provider_name,
            self.model_name,
            self.base_url,
        )
        payload = {
            "model": self.model_name,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        request = Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
                logger.info(
                    "ai_gateway_response trace_id=%s provider=%s model=%s usage=%s",
                    trace_id or "-",
                    self.provider_name,
                    response_payload.get("model") or self.model_name,
                    response_payload.get("usage", {}),
                )
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="ignore")
            logger.warning(
                "ai_gateway_http_error trace_id=%s provider=%s model=%s status=%s body=%s",
                trace_id or "-",
                self.provider_name,
                self.model_name,
                error.code,
                body,
            )
            raise AIClientError(body or f"AI provider http error: {error.code}") from error
        except URLError as error:
            logger.warning(
                "ai_gateway_network_error trace_id=%s provider=%s model=%s reason=%s",
                trace_id or "-",
                self.provider_name,
                self.model_name,
                error.reason,
            )
            raise AIClientError(f"AI provider network error: {error.reason}") from error
        except Exception as error:
            logger.warning(
                "ai_gateway_unknown_error trace_id=%s provider=%s model=%s error=%s",
                trace_id or "-",
                self.provider_name,
                self.model_name,
                error,
            )
            raise AIClientError(f"AI provider call failed: {error}") from error

        content = _extract_message_content(response_payload)
        if not content:
            raise AIClientError("AI provider returned empty content")

        return {
            "provider": self.provider_name,
            "model": response_payload.get("model") or self.model_name,
            "content": content,
            "usage": response_payload.get("usage", {}),
            "raw": response_payload,
        }


def _extract_message_content(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part).strip()

    return ""


def build_ai_client() -> BaseAIClient:
    settings = get_ai_settings()
    provider_config: Optional[AIProviderConfig] = settings.get_provider_config()

    if not settings.enabled or not provider_config:
        return DisabledAIClient()

    return OpenAICompatibleAIClient(
        config=provider_config,
        timeout_seconds=settings.timeout_seconds,
    )
