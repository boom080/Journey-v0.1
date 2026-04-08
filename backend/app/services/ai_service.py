import json
import logging
from functools import lru_cache
from typing import Any, Callable, Dict, Optional

from app.core.config import get_ai_settings
from app.schemas.ai_mini import (
    AICapability,
    AIRequestContext,
    AIResult,
    AIResultItem,
    SourceType,
)
from app.services.ai_client import AIClientError, build_ai_client
from app.services.ai_fallback import build_activity_fallback_result, build_food_fallback_result

logger = logging.getLogger("journey.ai.service")

DEFAULT_HOME_SUGGESTIONS = {
    "减脂": "今天优先保持真实记录，先把吃了什么和做了什么稳定记下来。",
    "增肌": "今天可以继续把饮食和训练一起记录，建议关注训练后的补充。",
    "维持": "今天继续轻量记录饮食和活动，保持日常节奏就很好。",
}


def _model_to_dict(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class JourneyAIService:
    def __init__(self):
        self.settings = get_ai_settings()
        self.client = build_ai_client()

    def estimate_food_from_text(
        self,
        text: str,
        context: Optional[AIRequestContext] = None,
        trace_id: str = "",
    ) -> AIResult:
        context = context or AIRequestContext()
        fallback = self._fallback_food_result(text=text, context=context, reason="ai_unavailable")

        return self._execute_json_capability(
            capability=AICapability.FOOD_TEXT_ESTIMATE,
            system_prompt=self._food_system_prompt(),
            user_prompt=self._food_user_prompt(text=text, context=context),
            builder=lambda payload, meta: self._build_food_result(payload, meta),
            fallback=fallback,
            trace_id=trace_id,
        )

    def estimate_activity_from_text(
        self,
        text: str,
        context: Optional[AIRequestContext] = None,
        trace_id: str = "",
    ) -> AIResult:
        context = context or AIRequestContext()
        fallback = self._fallback_activity_result(text=text, context=context, reason="ai_unavailable")

        return self._execute_json_capability(
            capability=AICapability.ACTIVITY_TEXT_ESTIMATE,
            system_prompt=self._activity_system_prompt(),
            user_prompt=self._activity_user_prompt(text=text, context=context),
            builder=lambda payload, meta: self._build_activity_result(payload, meta),
            fallback=fallback,
            trace_id=trace_id,
        )

    def generate_home_suggestion(
        self,
        context: Optional[AIRequestContext] = None,
        trace_id: str = "",
    ) -> AIResult:
        context = context or AIRequestContext()
        fallback = self._fallback_home_result(context=context, reason="ai_unavailable")

        return self._execute_json_capability(
            capability=AICapability.HOME_SUGGESTION,
            system_prompt=self._home_system_prompt(),
            user_prompt=self._home_user_prompt(context=context),
            builder=lambda payload, meta: self._build_home_result(payload, meta, context),
            fallback=fallback,
            trace_id=trace_id,
        )

    def _execute_json_capability(
        self,
        *,
        capability: AICapability,
        system_prompt: str,
        user_prompt: str,
        builder: Callable[[Dict[str, Any], Dict[str, Any]], AIResult],
        fallback: AIResult,
        trace_id: str = "",
    ) -> AIResult:
        if not self.settings.is_capability_enabled(capability.value):
            return self._merge_fallback_extra(
                fallback,
                {
                    "fallback_used": True,
                    "fallback_reason": "capability_disabled",
                    "provider": self.settings.provider,
                    "gateway_attempted": False,
                    "model_name": fallback.model,
                },
            )

        if not self.client.is_available():
            return self._merge_fallback_extra(
                fallback,
                {
                    "fallback_used": True,
                    "fallback_reason": "provider_not_configured",
                    "provider": self.settings.provider,
                    "gateway_attempted": False,
                    "model_name": fallback.model,
                },
            )

        try:
            logger.info(
                "ai_service_gateway_attempt trace_id=%s capability=%s provider=%s model=%s",
                trace_id or "-",
                capability.value,
                self.settings.provider,
                getattr(self.client, "model_name", ""),
            )
            raw_response = self.client.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                trace_id=trace_id,
            )
            payload = self._parse_json_payload(raw_response.get("content", ""))
            return builder(
                payload,
                {
                    "provider": raw_response.get("provider", self.settings.provider),
                    "model": raw_response.get("model", ""),
                    "usage": raw_response.get("usage", {}),
                },
            )
        except (AIClientError, ValueError, KeyError, TypeError) as error:
            fallback.extra["fallback_error"] = str(error)
            logger.info(
                "ai_service_fallback trace_id=%s capability=%s reason=%s",
                trace_id or "-",
                capability.value,
                "ai_runtime_error",
            )
            return self._merge_fallback_extra(
                fallback,
                {
                    "fallback_used": True,
                    "fallback_reason": "ai_runtime_error",
                    "provider": self.settings.provider,
                    "gateway_attempted": True,
                    "model_name": fallback.model,
                },
            )

    def _parse_json_payload(self, content: str) -> Dict[str, Any]:
        json_text = content.strip()
        if json_text.startswith("```"):
            start = json_text.find("{")
            end = json_text.rfind("}")
            if start != -1 and end != -1:
                json_text = json_text[start : end + 1]

        if not json_text:
            raise ValueError("AI returned empty text")

        return json.loads(json_text)

    def _build_food_result(self, payload: Dict[str, Any], meta: Dict[str, Any]) -> AIResult:
        items = []
        for item in payload.get("items") or []:
            items.append(
                AIResultItem(
                    title=str(item.get("title") or item.get("meal") or "饮食估算"),
                    name=item.get("name"),
                    detail=str(item.get("detail") or ""),
                    meal=item.get("meal"),
                    location=item.get("location"),
                    record_date=item.get("record_date"),
                    kcal=float(item.get("kcal") or 0),
                    time_text=item.get("time_text"),
                    source_type=SourceType.AI,
                    ai_type=AICapability.FOOD_TEXT_ESTIMATE.value,
                    extra=item.get("extra") or {},
                )
            )

        total_kcal = float(payload.get("total_kcal") or sum(item.kcal for item in items))

        return AIResult(
            capability=AICapability.FOOD_TEXT_ESTIMATE,
            provider=str(meta.get("provider") or self.settings.provider),
            model=str(meta.get("model") or ""),
            source_type=SourceType.AI,
            ai_type=AICapability.FOOD_TEXT_ESTIMATE.value,
            items=items,
            total_kcal=round(total_kcal, 2),
            summary=str(payload.get("summary") or "已生成饮食估算，请用户确认后再写入记录。"),
            extra={
                "usage": meta.get("usage") or {},
                "extra": payload.get("extra") or {},
                "fallback_used": False,
                "response_source": "gateway",
                "gateway_attempted": True,
                "model_name": str(meta.get("model") or ""),
            },
        )

    def _build_activity_result(self, payload: Dict[str, Any], meta: Dict[str, Any]) -> AIResult:
        items = []
        for item in payload.get("items") or []:
            items.append(
                AIResultItem(
                    title=str(item.get("title") or item.get("name") or "活动估算"),
                    name=str(item.get("name") or item.get("title") or "活动估算"),
                    detail=str(item.get("detail") or ""),
                    location=item.get("location"),
                    record_date=item.get("record_date"),
                    kcal=float(item.get("kcal") or 0),
                    time_text=item.get("time_text"),
                    source_type=SourceType.AI,
                    ai_type=AICapability.ACTIVITY_TEXT_ESTIMATE.value,
                    extra=item.get("extra") or {},
                )
            )

        total_kcal = float(payload.get("total_kcal") or sum(item.kcal for item in items))

        return AIResult(
            capability=AICapability.ACTIVITY_TEXT_ESTIMATE,
            provider=str(meta.get("provider") or self.settings.provider),
            model=str(meta.get("model") or ""),
            source_type=SourceType.AI,
            ai_type=AICapability.ACTIVITY_TEXT_ESTIMATE.value,
            items=items,
            total_kcal=round(total_kcal, 2),
            summary=str(payload.get("summary") or "已生成活动估算，请用户确认后再写入记录。"),
            extra={
                "usage": meta.get("usage") or {},
                "extra": payload.get("extra") or {},
                "fallback_used": False,
                "response_source": "gateway",
                "gateway_attempted": True,
                "model_name": str(meta.get("model") or ""),
            },
        )

    def _build_home_result(
        self,
        payload: Dict[str, Any],
        meta: Dict[str, Any],
        context: AIRequestContext,
    ) -> AIResult:
        summary = str(payload.get("summary") or "").strip()
        if not summary:
            summary = DEFAULT_HOME_SUGGESTIONS.get(context.goal or "维持", DEFAULT_HOME_SUGGESTIONS["维持"])

        return AIResult(
            capability=AICapability.HOME_SUGGESTION,
            provider=str(meta.get("provider") or self.settings.provider),
            model=str(meta.get("model") or ""),
            source_type=SourceType.AI,
            ai_type=AICapability.HOME_SUGGESTION.value,
            items=[],
            total_kcal=0,
            summary=summary,
            extra={
                "usage": meta.get("usage") or {},
                "extra": payload.get("extra") or {},
                "fallback_used": False,
                "response_source": "gateway",
                "gateway_attempted": True,
                "model_name": str(meta.get("model") or ""),
            },
        )

    def _fallback_food_result(self, text: str, context: AIRequestContext, reason: str) -> AIResult:
        result = build_food_fallback_result(
            text=text,
            context=context,
            provider=self.settings.provider,
            reason=reason,
        )
        result.extra.update(
            {
                "raw_text": text,
                "context": _model_to_dict(context),
                "response_source": "fallback_local",
                "gateway_attempted": True,
                "model_name": result.model,
            }
        )
        return result

    def _fallback_activity_result(self, text: str, context: AIRequestContext, reason: str) -> AIResult:
        result = build_activity_fallback_result(
            text=text,
            context=context,
            provider=self.settings.provider,
            reason=reason,
        )
        result.extra.update(
            {
                "raw_text": text,
                "context": _model_to_dict(context),
                "response_source": "fallback_local",
                "gateway_attempted": True,
                "model_name": result.model,
            }
        )
        return result

    def _fallback_home_result(self, context: AIRequestContext, reason: str) -> AIResult:
        summary = DEFAULT_HOME_SUGGESTIONS.get(context.goal or "维持", DEFAULT_HOME_SUGGESTIONS["维持"])

        return AIResult(
            capability=AICapability.HOME_SUGGESTION,
            provider=self.settings.provider,
            model="",
            source_type=SourceType.AI,
            ai_type=AICapability.HOME_SUGGESTION.value,
            items=[],
            total_kcal=0,
            summary=summary,
            extra={
                "fallback_used": True,
                "fallback_reason": reason,
                "context": _model_to_dict(context),
                "supported_future_types": ["image", "ocr", "pdf", "rag"],
                "response_source": "fallback_default",
                "gateway_attempted": True,
                "model_name": "",
            },
        )

    def _merge_fallback_extra(self, result: AIResult, extra_data: Dict[str, Any]) -> AIResult:
        next_extra = dict(result.extra)
        next_extra.update(extra_data)
        result.extra = next_extra
        return result

    def _food_system_prompt(self) -> str:
        return (
            "你是 Journey 的饮食估算助手。"
            "请把用户的一句话饮食描述解析成 JSON。"
            "只返回 JSON，不要返回 markdown。"
            "返回结构必须包含 items, total_kcal, summary, extra。"
            "items 内字段尽量包含 title, detail, meal, location, kcal, time_text, extra。"
        )

    def _food_user_prompt(self, text: str, context: AIRequestContext) -> str:
        return json.dumps(
            {
                "task": "food_text_estimate",
                "text": text,
                "context": _model_to_dict(context),
                "rules": {
                    "source_type": "ai",
                    "ai_type": AICapability.FOOD_TEXT_ESTIMATE.value,
                    "allow_empty_items_when_uncertain": True,
                },
            },
            ensure_ascii=False,
        )

    def _activity_system_prompt(self) -> str:
        return (
            "你是 Journey 的活动估算助手。"
            "请把用户的一句话活动描述解析成 JSON。"
            "只返回 JSON，不要返回 markdown。"
            "返回结构必须包含 items, total_kcal, summary, extra。"
            "items 内字段尽量包含 title, detail, location, kcal, time_text, extra。"
        )

    def _activity_user_prompt(self, text: str, context: AIRequestContext) -> str:
        return json.dumps(
            {
                "task": "activity_text_estimate",
                "text": text,
                "context": _model_to_dict(context),
                "rules": {
                    "source_type": "ai",
                    "ai_type": AICapability.ACTIVITY_TEXT_ESTIMATE.value,
                    "allow_empty_items_when_uncertain": True,
                },
            },
            ensure_ascii=False,
        )

    def _home_system_prompt(self) -> str:
        return (
            "你是 Journey 的首页建议助手。"
            "请基于用户当前目标和记录状态，生成一段轻陪伴语气的首页建议。"
            "只返回 JSON，不要返回 markdown。"
            "返回结构必须包含 items, total_kcal, summary, extra。"
            "items 可以为空数组。"
        )

    def _home_user_prompt(self, context: AIRequestContext) -> str:
        return json.dumps(
            {
                "task": "home_suggestion",
                "context": _model_to_dict(context),
                "rules": {
                    "tone": "light_companion",
                    "source_type": "ai",
                    "ai_type": AICapability.HOME_SUGGESTION.value,
                },
            },
            ensure_ascii=False,
        )


@lru_cache()
def get_ai_service() -> JourneyAIService:
    return JourneyAIService()
