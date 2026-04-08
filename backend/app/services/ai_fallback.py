import re
from typing import Dict, List, Optional

from app.schemas.ai_mini import AICapability, AIRequestContext, AIResult, AIResultItem, SourceType

FOOD_KEYWORD_KCAL = {
    "米饭": 230,
    "鸡胸肉": 220,
    "鸡蛋": 80,
    "牛奶": 120,
    "燕麦": 180,
    "牛肉": 260,
    "沙拉": 180,
    "面": 320,
    "面包": 180,
    "香蕉": 100,
    "苹果": 95,
}

ACTIVITY_KEYWORD_KCAL = {
    "跑步": 320,
    "慢跑": 260,
    "步行": 140,
    "骑行": 240,
    "游泳": 360,
    "力量训练": 220,
    "健身": 220,
    "羽毛球": 280,
    "篮球": 320,
    "跳绳": 300,
}

MEAL_KEYWORDS = {
    "早餐": ["早餐", "早饭", "早上"],
    "午餐": ["午餐", "中午", "午饭"],
    "晚餐": ["晚餐", "晚上", "晚饭"],
    "加餐": ["加餐", "夜宵", "零食"],
}

LOCATION_HINTS = ["公司", "家里", "学校", "食堂", "健身房", "操场", "办公室", "餐厅"]


def build_food_fallback_result(
    text: str,
    context: AIRequestContext,
    provider: str,
    reason: str,
    error_message: str = "",
) -> AIResult:
    items = _build_food_items(text, context)
    total_kcal = round(sum(item.kcal for item in items), 2)

    return AIResult(
        capability=AICapability.FOOD_TEXT_ESTIMATE,
        provider=provider,
        model="fallback-local-estimator",
        source_type=SourceType.AI,
        ai_type=AICapability.FOOD_TEXT_ESTIMATE.value,
        items=items,
        total_kcal=total_kcal,
        summary="AI 服务暂时不可用，已使用本地估算结果。你可以确认后直接写入，或继续手动修改。",
        extra={
            "fallback_used": True,
            "fallback_reason": reason,
            "fallback_error": error_message,
            "degrade_mode": "local_estimator",
            "supported_future_types": ["image", "ocr", "pdf", "rag"],
        },
    )


def build_activity_fallback_result(
    text: str,
    context: AIRequestContext,
    provider: str,
    reason: str,
    error_message: str = "",
) -> AIResult:
    items = _build_activity_items(text, context)
    total_kcal = round(sum(item.kcal for item in items), 2)

    return AIResult(
        capability=AICapability.ACTIVITY_TEXT_ESTIMATE,
        provider=provider,
        model="fallback-local-estimator",
        source_type=SourceType.AI,
        ai_type=AICapability.ACTIVITY_TEXT_ESTIMATE.value,
        items=items,
        total_kcal=total_kcal,
        summary="AI 服务暂时不可用，已使用本地估算结果。你可以确认后直接写入，或继续手动修改。",
        extra={
            "fallback_used": True,
            "fallback_reason": reason,
            "fallback_error": error_message,
            "degrade_mode": "local_estimator",
            "supported_future_types": ["image", "ocr", "pdf", "rag"],
        },
    )


def _build_food_items(text: str, context: AIRequestContext) -> List[AIResultItem]:
    meal = _infer_meal(text, context.extra.get("meal") if context.extra else None)
    location = _infer_location(text, context.extra.get("location") if context.extra else None)
    time_text = context.extra.get("time_text") if context.extra else None
    record_date = context.record_date
    candidates = _split_text_items(text)

    items: List[AIResultItem] = []
    for candidate in candidates:
        kcal = _extract_explicit_kcal(candidate) or _estimate_by_keywords(candidate, FOOD_KEYWORD_KCAL, 260)
        items.append(
            AIResultItem(
                title=meal,
                detail=candidate,
                meal=meal,
                location=location,
                record_date=record_date,
                kcal=float(kcal),
                time_text=time_text,
                source_type=SourceType.AI,
                ai_type=AICapability.FOOD_TEXT_ESTIMATE.value,
                extra={"estimation_mode": "keyword"},
            )
        )

    if items:
        return items

    return [
        AIResultItem(
            title=meal,
            detail=text.strip(),
            meal=meal,
            location=location,
            record_date=record_date,
            kcal=float(_estimate_by_keywords(text, FOOD_KEYWORD_KCAL, 260)),
            time_text=time_text,
            source_type=SourceType.AI,
            ai_type=AICapability.FOOD_TEXT_ESTIMATE.value,
            extra={"estimation_mode": "keyword"},
        )
    ]


def _build_activity_items(text: str, context: AIRequestContext) -> List[AIResultItem]:
    location = _infer_location(text, context.extra.get("location") if context.extra else None)
    time_text = context.extra.get("time_text") if context.extra else None
    record_date = context.record_date
    candidates = _split_text_items(text)

    items: List[AIResultItem] = []
    for candidate in candidates:
        name = _infer_activity_name(candidate)
        kcal = _extract_explicit_kcal(candidate) or _estimate_by_keywords(candidate, ACTIVITY_KEYWORD_KCAL, 180)
        items.append(
            AIResultItem(
                title=name,
                name=name,
                detail=candidate,
                location=location,
                record_date=record_date,
                kcal=float(kcal),
                time_text=time_text,
                source_type=SourceType.AI,
                ai_type=AICapability.ACTIVITY_TEXT_ESTIMATE.value,
                extra={"estimation_mode": "keyword"},
            )
        )

    if items:
        return items

    return [
        AIResultItem(
            title=_infer_activity_name(text),
            name=_infer_activity_name(text),
            detail=text.strip(),
            location=location,
            record_date=record_date,
            kcal=float(_estimate_by_keywords(text, ACTIVITY_KEYWORD_KCAL, 180)),
            time_text=time_text,
            source_type=SourceType.AI,
            ai_type=AICapability.ACTIVITY_TEXT_ESTIMATE.value,
            extra={"estimation_mode": "keyword"},
        )
    ]


def _split_text_items(text: str) -> List[str]:
    raw_parts = re.split(r"[，,、；;。]|和", text)
    return [part.strip() for part in raw_parts if part and part.strip()]


def _extract_explicit_kcal(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kcal|卡|千卡)", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _estimate_by_keywords(text: str, keyword_map: Dict[str, int], default_kcal: int) -> int:
    score = 0
    for keyword, kcal in keyword_map.items():
        if keyword in text:
            score += kcal

    if score > 0:
        return score

    return default_kcal


def _infer_meal(text: str, default_meal: Optional[str]) -> str:
    if default_meal:
        return default_meal

    for meal, keywords in MEAL_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return meal

    return "早餐"


def _infer_location(text: str, default_location: Optional[str]) -> str:
    if default_location:
        return default_location

    for keyword in LOCATION_HINTS:
        if keyword in text:
            return keyword

    return ""


def _infer_activity_name(text: str) -> str:
    for keyword in ACTIVITY_KEYWORD_KCAL:
        if keyword in text:
            return keyword
    return "活动估算"
