import json
import logging
from functools import lru_cache
from typing import Any, Callable, Dict, Optional

from app.core.config import AIModelCandidate, get_ai_settings
from app.core.logging import build_error_log_fields, normalize_log_value
from app.schemas.ai_mini import (
    AICapability,
    AIRequestContext,
    AIResult,
    AIResultItem,
    SourceType,
)
from app.services.ai_client import AIClientError, build_ai_client
from app.services.ai_fallback import build_activity_fallback_result, build_food_fallback_result

logger = logging.getLogger("journey.mini.ai.service")

DEFAULT_HOME_SUGGESTIONS = {
    "减脂": "把节奏放轻一点也没关系，先把手边的一餐一动慢慢记清，心里会更踏实。",
    "增肌": "把补给和动作慢慢对齐就很好，稳稳吃好也稳稳练着，状态会自己跟上来。",
    "维持": "照着自己的节奏慢慢来就好，把日常轻轻接住，今天也会顺顺当当过去。",
}


def _model_to_dict(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class JourneyAIService:
    def __init__(self):
        self.settings = get_ai_settings()

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
        capability_name = capability.value
        candidates = self.settings.get_candidates_for_capability(capability_name)
        attempted_models = []
        gateway_attempted = False
        last_error = build_error_log_fields()

        if not self.settings.is_capability_enabled(capability_name):
            return self._merge_fallback_extra(
                fallback,
                {
                    "fallback_used": True,
                    "fallback_reason": "capability_disabled",
                    "provider": self.settings.provider,
                    "gateway_attempted": False,
                    "model_name": fallback.model,
                    "attempted_models": attempted_models,
                    "fallback_to": "local_fallback",
                    "fallback_error": "none",
                    "fallback_error_type": "-",
                    "fallback_error_message": "-",
                },
            )

        if not candidates:
            return self._merge_fallback_extra(
                fallback,
                {
                    "fallback_used": True,
                    "fallback_reason": "model_candidates_not_configured",
                    "provider": self.settings.provider,
                    "gateway_attempted": False,
                    "model_name": fallback.model,
                    "attempted_models": attempted_models,
                    "fallback_to": "local_fallback",
                    "fallback_error": "No model candidates configured",
                    "fallback_error_type": "ModelRoutingError",
                    "fallback_error_message": "No model candidates configured",
                },
            )

        for index, candidate in enumerate(candidates):
            fallback_to = self._candidate_label(candidates[index + 1]) if index + 1 < len(candidates) else "local_fallback"
            provider_config = self.settings.get_provider_config(candidate.provider)

            if not provider_config:
                error_fields = build_error_log_fields(f"{candidate.provider} provider is not configured")
                attempted_models.append(self._build_attempt_item(candidate, "skipped", error_fields))
                last_error = error_fields
                logger.warning(
                    "ai_service_candidate_skipped trace_id=%s capability=%s provider=%s model=%s error=%s error_type=%s error_message=%s fallback_to=%s",
                    trace_id or "-",
                    capability_name,
                    candidate.provider,
                    candidate.model,
                    error_fields["error"],
                    error_fields["error_type"],
                    error_fields["error_message"],
                    fallback_to,
                )
                continue

            client = build_ai_client(candidate.provider, candidate.model)
            if not client.is_available():
                error_fields = build_error_log_fields("AI client is unavailable")
                attempted_models.append(self._build_attempt_item(candidate, "skipped", error_fields))
                last_error = error_fields
                logger.warning(
                    "ai_service_candidate_skipped trace_id=%s capability=%s provider=%s model=%s error=%s error_type=%s error_message=%s fallback_to=%s",
                    trace_id or "-",
                    capability_name,
                    candidate.provider,
                    candidate.model,
                    error_fields["error"],
                    error_fields["error_type"],
                    error_fields["error_message"],
                    fallback_to,
                )
                continue

            gateway_attempted = True
            logger.info(
                "ai_service_gateway_attempt trace_id=%s capability=%s provider=%s model=%s attempt=%s total=%s error=%s fallback_to=%s",
                trace_id or "-",
                capability_name,
                candidate.provider,
                candidate.model,
                index + 1,
                len(candidates),
                "none",
                fallback_to,
            )

            try:
                raw_response = client.chat(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    trace_id=trace_id,
                )
                payload = self._parse_json_payload(raw_response.get("content", ""))
                selected_model = normalize_log_value(raw_response.get("model") or candidate.model, candidate.model)
                selected_provider = normalize_log_value(raw_response.get("provider") or candidate.provider, candidate.provider)
                attempted_models.append(
                    self._build_attempt_item(
                        AIModelCandidate(provider=selected_provider, model=selected_model, supports_vision=candidate.supports_vision),
                        "success",
                    )
                )
                logger.info(
                    "ai_service_gateway_success trace_id=%s capability=%s provider=%s model=%s attempt=%s total=%s error=%s",
                    trace_id or "-",
                    capability_name,
                    selected_provider,
                    selected_model,
                    index + 1,
                    len(candidates),
                    "none",
                )
                result = builder(
                    payload,
                    {
                        "provider": selected_provider,
                        "model": selected_model,
                        "usage": raw_response.get("usage", {}),
                    },
                )
                return self._merge_fallback_extra(
                    result,
                    {
                        "gateway_attempted": True,
                        "selected_provider": selected_provider,
                        "selected_model": selected_model,
                        "model_name": selected_model,
                        "attempted_models": attempted_models,
                        "model_fallback_used": index > 0,
                        "fallback_to": f"{selected_provider}:{selected_model}" if index > 0 else "-",
                        "fallback_error": "none",
                        "fallback_error_type": "-",
                        "fallback_error_message": "-",
                    },
                )
            except (AIClientError, ValueError, KeyError, TypeError) as error:
                error_fields = build_error_log_fields(error)
                attempted_models.append(self._build_attempt_item(candidate, "failed", error_fields))
                last_error = error_fields
                logger.warning(
                    "ai_service_gateway_failure trace_id=%s capability=%s provider=%s model=%s attempt=%s total=%s error=%s error_type=%s error_message=%s fallback_to=%s",
                    trace_id or "-",
                    capability_name,
                    candidate.provider,
                    candidate.model,
                    index + 1,
                    len(candidates),
                    error_fields["error"],
                    error_fields["error_type"],
                    error_fields["error_message"],
                    fallback_to,
                )

        logger.warning(
            "ai_service_fallback trace_id=%s capability=%s source=%s provider=%s model=%s error=%s error_type=%s error_message=%s fallback_to=%s",
            trace_id or "-",
            capability_name,
            fallback.extra.get("response_source", "fallback_local"),
            fallback.provider,
            fallback.model or "-",
            last_error["error"],
            last_error["error_type"],
            last_error["error_message"],
            "local_fallback",
        )
        return self._merge_fallback_extra(
            fallback,
            {
                "fallback_used": True,
                "fallback_reason": "ai_runtime_error",
                "provider": self.settings.provider,
                "gateway_attempted": gateway_attempted,
                "model_name": fallback.model,
                "attempted_models": attempted_models,
                "fallback_to": "local_fallback",
                "fallback_error": last_error["error"],
                "fallback_error_type": last_error["error_type"],
                "fallback_error_message": last_error["error_message"],
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
                    title=str(item.get("title") or item.get("meal") or item.get("detail") or "饮食估算"),
                    name=str(item.get("name") or item.get("food_name") or item.get("title") or item.get("detail") or ""),
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
                "gateway_attempted": False,
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
                "gateway_attempted": False,
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
                "gateway_attempted": False,
                "model_name": "",
            },
        )

    def _merge_fallback_extra(self, result: AIResult, extra_data: Dict[str, Any]) -> AIResult:
        next_extra = dict(result.extra)
        next_extra.update(extra_data)
        result.extra = next_extra
        return result

    def _build_attempt_item(
        self,
        candidate: AIModelCandidate,
        status: str,
        error_fields: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        fields = error_fields or build_error_log_fields()
        return {
            "provider": candidate.provider,
            "model": candidate.model,
            "status": status,
            "error": fields["error"],
            "error_type": fields["error_type"],
            "error_message": fields["error_message"],
        }

    def _candidate_label(self, candidate: AIModelCandidate) -> str:
        return f"{candidate.provider}:{candidate.model}"

    def _food_system_prompt(self) -> str:
        return (
            "你是 Journey 的饮食估算助手。"
            "请把用户的一句话饮食描述解析成 JSON。"
            "只返回 JSON，不要返回 markdown。"
            "返回结构必须包含 items, total_kcal, summary, extra。"
            "items 内字段尽量包含 title, name, detail, meal, location, kcal, time_text, extra。"
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
            "你是 Journey 的“今日贴纸”文案助手。"
            "请基于用户当前目标和记录状态，生成一句贴纸式的轻陪伴提醒。"
            "只返回 JSON，不要返回 markdown。"
            "返回结构必须包含 items, total_kcal, summary, extra。"
            "items 可以为空数组。"
            "summary 必须是一整段中文，不换行，不分点，不加标题，不加前缀标签。"
            "summary 控制在 30 到 55 个汉字之间。"
            "语气要轻松、温和、略带俏皮，但不要幼稚，不要写成系统播报或数据汇报。"
            "尽量少提数字，不要反复使用“今天、记录、热量”这类机械词。"
            "如果数据明显异常，只做温和提醒，不夸张、不乱鼓励。"
        )

    def _home_user_prompt(self, context: AIRequestContext) -> str:
        return json.dumps(
            {
                "task": "home_suggestion",
                "context": _model_to_dict(context),
                "rules": {
                    "tone": "gentle_playful_sticker",
                    "format": "single_paragraph_only",
                    "line_breaks": "forbidden",
                    "length_cn_chars": "30-55",
                    "avoid_style": ["system_broadcast", "data_report", "bullet_points", "title_prefix"],
                    "avoid_words": ["今天", "记录", "热量"],
                    "number_density": "low",
                    "when_data_is_abnormal": "warm_neutral_reminder",
                    "source_type": "ai",
                    "ai_type": AICapability.HOME_SUGGESTION.value,
                },
            },
            ensure_ascii=False,
        )


@lru_cache()
def get_ai_service() -> JourneyAIService:
    return JourneyAIService()
