import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps_mini import get_activated_user, get_db
from app.models.user import User
from app.schemas.ai_mini import (
    AIRequestContext,
    AIResult,
    ActivityTextEstimateRequest,
    FoodTextEstimateRequest,
    HomeSuggestionRequest,
    SourceType,
)
from app.services.ai_service import get_ai_service
from app.services.home_mini import build_home_summary

logger = logging.getLogger("journey.ai.route")

router = APIRouter(prefix="/ai", tags=["AI"])


def _model_to_dict(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _build_context(
    current_user: User,
    *,
    record_date: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> AIRequestContext:
    return AIRequestContext(
        user_id=current_user.id,
        nickname=current_user.nickname,
        goal=current_user.goal,
        record_date=record_date,
        extra=extra or {},
    )


def _merge_extra(result: AIResult, extra_data: Dict[str, Any]) -> AIResult:
    next_extra = dict(result.extra)
    next_extra.update(extra_data)
    result.extra = next_extra
    return result


def _fill_food_defaults(result: AIResult, payload: FoodTextEstimateRequest) -> AIResult:
    for item in result.items:
        if payload.record_date and not item.record_date:
            item.record_date = payload.record_date
        if payload.time_text and not item.time_text:
            item.time_text = payload.time_text
        if payload.meal and not item.meal:
            item.meal = payload.meal
        if payload.location and not item.location:
            item.location = payload.location

    return _merge_extra(
        result,
        {
            "record_defaults": {
                "record_date": payload.record_date,
                "time_text": payload.time_text,
                "meal": payload.meal,
                "location": payload.location,
                "source_type": SourceType.AI.value,
                "confirmation_required": True,
            }
        },
    )


def _fill_activity_defaults(result: AIResult, payload: ActivityTextEstimateRequest) -> AIResult:
    for item in result.items:
        if payload.record_date and not item.record_date:
            item.record_date = payload.record_date
        if payload.time_text and not item.time_text:
            item.time_text = payload.time_text
        if payload.location and not item.location:
            item.location = payload.location
        if not item.name:
            item.name = item.title or "活动估算"

    return _merge_extra(
        result,
        {
            "record_defaults": {
                "record_date": payload.record_date,
                "time_text": payload.time_text,
                "location": payload.location,
                "source_type": SourceType.AI.value,
                "confirmation_required": True,
            }
        },
    )


def _attach_trace(result: AIResult, trace_id: str) -> AIResult:
    return _merge_extra(
        result,
        {
            "trace_id": trace_id,
            "response_source": result.extra.get("response_source", "unknown"),
            "model_name": result.extra.get("model_name") or result.model or "",
        },
    )


@router.post("/food-text-estimate", response_model=AIResult)
def estimate_food_text(
    payload: FoodTextEstimateRequest,
    current_user: User = Depends(get_activated_user),
):
    trace_id = uuid4().hex[:12]
    prompt_preview = payload.text.strip().replace("\n", " ")[:80]
    logger.info(
        "ai_food_estimate_request trace_id=%s endpoint=food-text-estimate user_id=%s prompt_preview=%s",
        trace_id,
        current_user.id,
        prompt_preview,
    )

    service = get_ai_service()
    result = service.estimate_food_from_text(
        text=payload.text,
        trace_id=trace_id,
        context=_build_context(
            current_user,
            record_date=payload.record_date,
            extra={
                "meal": payload.meal,
                "time_text": payload.time_text,
                "location": payload.location,
                **payload.extra,
            },
        ),
    )
    result = _fill_food_defaults(result, payload)
    result = _attach_trace(result, trace_id)
    logger.info(
        "ai_food_estimate_result trace_id=%s endpoint=food-text-estimate gateway_attempted=%s source=%s provider=%s model=%s error=%s",
        trace_id,
        result.extra.get("gateway_attempted"),
        result.extra.get("response_source"),
        result.provider,
        result.extra.get("model_name") or result.model,
        result.extra.get("fallback_error", ""),
    )
    return result


@router.post("/activity-text-estimate", response_model=AIResult)
def estimate_activity_text(
    payload: ActivityTextEstimateRequest,
    current_user: User = Depends(get_activated_user),
):
    trace_id = uuid4().hex[:12]
    prompt_preview = payload.text.strip().replace("\n", " ")[:80]
    logger.info(
        "ai_activity_estimate_request trace_id=%s endpoint=activity-text-estimate user_id=%s prompt_preview=%s",
        trace_id,
        current_user.id,
        prompt_preview,
    )

    service = get_ai_service()
    result = service.estimate_activity_from_text(
        text=payload.text,
        trace_id=trace_id,
        context=_build_context(
            current_user,
            record_date=payload.record_date,
            extra={
                "time_text": payload.time_text,
                "location": payload.location,
                **payload.extra,
            },
        ),
    )
    result = _fill_activity_defaults(result, payload)
    result = _attach_trace(result, trace_id)
    logger.info(
        "ai_activity_estimate_result trace_id=%s endpoint=activity-text-estimate gateway_attempted=%s source=%s provider=%s model=%s error=%s",
        trace_id,
        result.extra.get("gateway_attempted"),
        result.extra.get("response_source"),
        result.provider,
        result.extra.get("model_name") or result.model,
        result.extra.get("fallback_error", ""),
    )
    return result


@router.post("/home-suggestion", response_model=AIResult)
def generate_home_suggestion(
    payload: Optional[HomeSuggestionRequest] = Body(default=None),
    current_user: User = Depends(get_activated_user),
    db: Session = Depends(get_db),
):
    trace_id = uuid4().hex[:12]
    logger.info("ai_home_suggestion_request trace_id=%s user_id=%s", trace_id, current_user.id)

    request_payload = payload or HomeSuggestionRequest()
    base_summary = build_home_summary(db, current_user)

    result = get_ai_service().generate_home_suggestion(
        trace_id=trace_id,
        context=_build_context(
            current_user,
            extra={
                "today_summary": request_payload.today_summary or base_summary.get("today_summary", ""),
                "intake_kcal": request_payload.intake_kcal
                if request_payload.intake_kcal is not None
                else base_summary.get("intake_kcal", 0),
                "activity_kcal": request_payload.activity_kcal
                if request_payload.activity_kcal is not None
                else base_summary.get("activity_kcal", 0),
                "net_kcal": request_payload.net_kcal
                if request_payload.net_kcal is not None
                else base_summary.get("net_kcal", 0),
                "recent_updates": request_payload.recent_updates or base_summary.get("recent_updates", []),
                **request_payload.extra,
            },
        )
    )

    result = _merge_extra(
        result,
        {
            "context_snapshot": {
                "goal": current_user.goal,
                "today_summary": request_payload.today_summary or base_summary.get("today_summary", ""),
                "recent_updates_count": len(request_payload.recent_updates or base_summary.get("recent_updates", [])),
            },
            "base_summary": base_summary,
            "request_overrides": _model_to_dict(request_payload),
            "trace_id": trace_id,
        },
    )
    logger.info(
        "ai_home_suggestion_result trace_id=%s endpoint=home-suggestion gateway_attempted=%s source=%s provider=%s model=%s error=%s",
        trace_id,
        result.extra.get("gateway_attempted"),
        result.extra.get("response_source"),
        result.provider,
        result.extra.get("model_name") or result.model,
        result.extra.get("fallback_error", ""),
    )
    return result
