import base64
import binascii
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLMRouter
from litellm import Router as LiteLLMRouter
from openai import OpenAIError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.model_router import KNOWLEDGE_VERSION
from app.agent.provider_profiles import get_provider_profile, litellm_model_name
from app.agent.tools import add_tool_trace, create_confirmation
from app.api.errors import APIError
from app.core.settings import Settings, get_settings
from app.models.agent import AgentRun
from app.models.user import User
from app.schemas.agent import AgentUsage, FoodAgentCandidate
from app.schemas.media import (
    FoodImageAnalysisResponse,
    FoodImageAnalyzeRequest,
    FoodImageEstimate,
    FoodImageItem,
    FoodImageScaleReferenceType,
)
from app.schemas.records import FoodRecordCreate
from app.services.agent_privacy import prepare_agent_access

FOOD_IMAGE_PROMPT_VERSION = "journey-food-image-1.3.0"
FOOD_IMAGE_SCHEMA_VERSION = "journey-food-image-schema-3"


@dataclass(frozen=True)
class FoodImageInvocation:
    output: FoodImageEstimate | None
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    estimated_cost_usd: float
    fallback_used: bool
    error_code: str | None = None


class FoodImageAnalyzer:
    provider: str
    model: str

    def analyze(
        self,
        *,
        data_url: str,
        note: str | None,
        meal_type_hint: str,
        scale_reference_type: FoodImageScaleReferenceType,
        scale_reference_size_cm: float | None,
    ) -> FoodImageInvocation:
        raise NotImplementedError


class MockFoodImageAnalyzer(FoodImageAnalyzer):
    provider = "mock"
    model = "journey-food-image-mock-v1"

    def analyze(
        self,
        *,
        data_url: str,
        note: str | None,
        meal_type_hint: str,
        scale_reference_type: FoodImageScaleReferenceType,
        scale_reference_size_cm: float | None,
    ) -> FoodImageInvocation:
        started = time.perf_counter()
        name = (note or "待确认的一餐").strip()[:120] or "待确认的一餐"
        output = FoodImageEstimate(
            is_food=True,
            name=name,
            items=[
                FoodImageItem(
                    name=name,
                    portion_amount=1,
                    portion_unit="份",
                    energy_kcal=300,
                )
            ],
            meal_type=meal_type_hint,
            portion_amount=1,
            portion_unit="份",
            energy_kcal=300,
            energy_min_kcal=180,
            energy_max_kcal=450,
            confidence="low",
            assumptions=["Mock 演示值，未真实识别图片", "默认按一份普通餐食估算"],
            scale_reference_used=False,
        )
        return FoodImageInvocation(
            output=output,
            provider=self.provider,
            model=self.model,
            input_tokens=0,
            output_tokens=0,
            latency_ms=int((time.perf_counter() - started) * 1000),
            estimated_cost_usd=0,
            fallback_used=True,
        )


class LangChainLiteLLMFoodImageAnalyzer(FoodImageAnalyzer):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.food_image_provider
        self.model = settings.food_image_model
        profile = get_provider_profile(self.provider)
        params = {
            "model": litellm_model_name(profile, self.model),
            "api_key": settings.food_image_api_key,
            "timeout": settings.agent_timeout_seconds,
            "max_retries": 0,
            "temperature": 0,
        }
        if settings.food_image_api_base_url:
            params["api_base"] = settings.food_image_api_base_url
        if self.provider == "qwen":
            params["extra_body"] = {"enable_thinking": False}
        route_name = f"journey-food-image-{self.provider}-{self.model}"
        router = LiteLLMRouter(
            model_list=[{"model_name": route_name, "litellm_params": params}],
            num_retries=0,
            max_fallbacks=0,
            timeout=settings.agent_timeout_seconds,
            cache_responses=False,
            disable_cooldowns=True,
        )
        self.chat = ChatLiteLLMRouter(
            router=router,
            model=route_name,
            temperature=0,
            request_timeout=settings.agent_timeout_seconds,
            max_retries=0,
        )

    def analyze(
        self,
        *,
        data_url: str,
        note: str | None,
        meal_type_hint: str,
        scale_reference_type: FoodImageScaleReferenceType,
        scale_reference_size_cm: float | None,
    ) -> FoodImageInvocation:
        started = time.perf_counter()
        system_prompt = (
            "你是 Journey 的食物图片候选分析器。只分析食物，不分析人物、身体或身份。"
            "仅输出一个 JSON 对象，不要 Markdown。不是食物或无法判断时 is_food=false。"
            "食物时严格使用这些键：is_food=true；name=通用中文名；"
            "canonical_name_en=简短规范英文名；items=最多3个主要食物，每项含 name、"
            "canonical_name_en、portion_amount、portion_unit、energy_kcal；"
            "meal_type 只能是 breakfast/lunch/dinner/snack/other；"
            "portion_amount=整图可见食物总量，固体 portion_unit=g、饮料=ml；"
            "energy_kcal 必须给点估计；energy_min_kcal 与 energy_max_kcal 给宽区间；"
            "confidence 只能是 low/medium；assumptions 最多3条；"
            "scale_reference_used 只能是 true/false；仅当声明的参照在图中完整可见、"
            "与食物几何关系可信且确实用于份量推断时才为 true，否则 false 并说明原因；"
            "needs_user_correction=true。"
            "非食物 JSON 示例："
            '{"is_food":false,"name":null,"canonical_name_en":null,"items":[],'
            '"meal_type":"other","portion_amount":null,"portion_unit":null,'
            '"energy_kcal":null,"energy_min_kcal":null,"energy_max_kcal":null,'
            '"confidence":"low","assumptions":["非食物"],"scale_reference_used":false,'
            '"needs_user_correction":true}'
        )
        user_text = (
            f"餐别提示：{meal_type_hint}。"
            f"用户补充：{note or '无'}。"
            f"{_scale_reference_instruction(scale_reference_type, scale_reference_size_cm)}"
            "分析图片中的食物；needs_user_correction 必须为 true。"
        )
        result = self.chat.with_structured_output(
            FoodImageEstimate,
            method="json_mode",
            include_raw=True,
        ).invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=[
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ]
                ),
            ]
        )
        raw = result.get("raw") if isinstance(result, dict) else None
        parsed = result.get("parsed") if isinstance(result, dict) else None
        usage = getattr(raw, "usage_metadata", None) or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        cost = (
            input_tokens * self.settings.food_image_input_usd_per_million
            + output_tokens * self.settings.food_image_output_usd_per_million
        ) / 1_000_000
        try:
            output = _safe_food_image_estimate(parsed, raw)
        except ValueError:
            return FoodImageInvocation(
                output=None,
                provider=self.provider,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=int((time.perf_counter() - started) * 1000),
                estimated_cost_usd=round(cost, 8),
                fallback_used=True,
                error_code="invalid_structured_output",
            )
        if scale_reference_type == "none" and output.scale_reference_used:
            output = output.model_copy(
                update={
                    "scale_reference_used": False,
                    "assumptions": [
                        *output.assumptions[:4],
                        "用户未声明尺度参照，未采用参照尺寸",
                    ],
                }
            )
        return FoodImageInvocation(
            output=output,
            provider=self.provider,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
            estimated_cost_usd=round(cost, 8),
            fallback_used=False,
        )


def _scale_reference_instruction(
    reference_type: FoodImageScaleReferenceType,
    size_cm: float | None,
) -> str:
    if reference_type == "journey_card":
        return (
            "尺度参照：用户声明图中放置了一张完整的 Journey 高对比参照卡，"
            "实体尺寸为 9×5 cm；只有卡片完整可见且与食物处于近似同一平面时才使用。"
        )
    if reference_type == "plate_diameter" and size_cm is not None:
        return (
            f"尺度参照：用户声明完整可见的餐盘外沿直径为 {size_cm:g} cm；"
            "盘沿不完整、严重透视或不是承载食物的同一餐盘时不得使用。"
        )
    if reference_type == "bowl_diameter" and size_cm is not None:
        return (
            f"尺度参照：用户声明完整可见的碗口直径为 {size_cm:g} cm；"
            "碗口不完整、严重透视或不是承载食物的同一碗时不得使用。"
        )
    return "尺度参照：无。不得根据未声明物体假设真实尺寸，份量保持保守宽估计。"


def _raw_json_object(raw: object) -> dict[str, object] | None:
    content = getattr(raw, "content", None)
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        content = "".join(
            str(item.get("text") or "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    if not isinstance(content, str):
        return None
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = candidate.removeprefix("```json").removeprefix("```")
        candidate = candidate.removesuffix("```").strip()
    try:
        payload = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _safe_number(value: object) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _safe_food_image_estimate(
    parsed: object,
    raw: object,
) -> FoodImageEstimate:
    if isinstance(parsed, FoodImageEstimate):
        payload = parsed.model_dump()
    elif isinstance(parsed, dict):
        payload = dict(parsed)
    else:
        payload = _raw_json_object(raw)
    if payload is None or not isinstance(payload.get("is_food"), bool):
        raise ValueError("vision provider returned invalid structured output")

    normalized = False
    is_food = bool(payload["is_food"])
    if payload.get("confidence") not in {"low", "medium"}:
        payload["confidence"] = "medium" if is_food else "low"
        normalized = True
    if payload.get("meal_type") not in {"breakfast", "lunch", "dinner", "snack", "other"}:
        payload["meal_type"] = "other"
        normalized = True
    if payload.get("needs_user_correction") is not True:
        payload["needs_user_correction"] = True
        normalized = True
    if not isinstance(payload.get("scale_reference_used"), bool):
        payload["scale_reference_used"] = False
        normalized = True

    items = payload.get("items")
    if not isinstance(items, list):
        items = []
        normalized = True
    cleaned_items = [dict(item) for item in items[:8] if isinstance(item, dict)]
    if cleaned_items != items:
        normalized = True
    payload["items"] = cleaned_items

    if is_food:
        point = _safe_number(payload.get("energy_kcal"))
        current_minimum = _safe_number(payload.get("energy_min_kcal"))
        current_maximum = _safe_number(payload.get("energy_max_kcal"))
        if point is None and current_minimum is not None and current_maximum is not None:
            point = (current_minimum + current_maximum) / 2
            payload["energy_kcal"] = point
            normalized = True
        if point is not None:
            broad_minimum = max(0.0, point * 0.25)
            broad_maximum = point * 2.0
            payload["energy_min_kcal"] = min(
                current_minimum if current_minimum is not None else broad_minimum,
                broad_minimum,
            )
            payload["energy_max_kcal"] = max(
                current_maximum if current_maximum is not None else broad_maximum,
                broad_maximum,
            )
            normalized = normalized or (
                current_minimum != payload["energy_min_kcal"]
                or current_maximum != payload["energy_max_kcal"]
            )

    assumptions = payload.get("assumptions")
    if not isinstance(assumptions, list):
        assumptions = []
        normalized = True
    assumptions = [str(item)[:200] for item in assumptions[:5]]
    if normalized and len(assumptions) < 5:
        assumptions.append("Provider 输出已归一化为 Journey 安全候选，仍需用户校正")
    payload["assumptions"] = assumptions
    return FoodImageEstimate.model_validate(payload)


def _decode_image(payload: FoodImageAnalyzeRequest, settings: Settings) -> bytes:
    if (
        payload.width > settings.food_image_max_dimension
        or payload.height > settings.food_image_max_dimension
    ):
        raise APIError(
            status_code=422,
            code="food_image_dimensions_exceeded",
            message="Image dimensions exceed the configured limit",
        )
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise APIError(
            status_code=422,
            code="invalid_food_image_base64",
            message="Image data is not valid base64",
        ) from error
    if len(image_bytes) > settings.food_image_max_bytes:
        raise APIError(
            status_code=413,
            code="food_image_too_large",
            message="Image exceeds the configured byte limit",
        )
    signatures = {
        "image/jpeg": image_bytes.startswith(b"\xff\xd8\xff"),
        "image/png": image_bytes.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP",
    }
    if not signatures[payload.media_type]:
        raise APIError(
            status_code=422,
            code="food_image_type_mismatch",
            message="Image bytes do not match the declared media type",
        )
    return image_bytes


def _usage(invocation: FoodImageInvocation) -> AgentUsage:
    return AgentUsage(
        provider=invocation.provider,
        model=invocation.model,
        input_tokens=invocation.input_tokens,
        output_tokens=invocation.output_tokens,
        retries=0,
        latency_ms=invocation.latency_ms,
        estimated_cost_usd=invocation.estimated_cost_usd,
    )


def analyze_food_image(
    db: Session,
    user: User,
    *,
    payload: FoodImageAnalyzeRequest,
    request_id: str,
    settings: Settings | None = None,
    analyzer: FoodImageAnalyzer | None = None,
) -> FoodImageAnalysisResponse:
    settings = settings or get_settings()
    if not settings.food_image_analysis_enabled:
        raise APIError(
            status_code=503,
            code="food_image_analysis_disabled",
            message="Food image analysis is disabled; use manual food entry",
        )
    # A personal local install may use an external image provider after the
    # operator-level switch and the request's explicit confirm_upload=true.
    # Test, staging and production remain fail-closed until a dedicated image
    # privacy contract is implemented.
    uses_external_image_provider = settings.food_image_provider != "mock" or (
        analyzer is not None and analyzer.provider != "mock"
    )
    local_personal_image_mode = (
        settings.environment == "local" and settings.food_image_external_upload_confirmed
    )
    if uses_external_image_provider and not local_personal_image_mode:
        raise APIError(
            status_code=503,
            code="food_image_external_disabled",
            message="外部图片分析仅在本机个人使用模式开放，请使用手动饮食记录",
        )
    # Mock image candidates share AgentRun storage and the deletion barrier.
    prepare_agent_access(db, user.id)
    image_bytes = _decode_image(payload, settings)
    data_url = f"data:{payload.media_type};base64,{payload.image_base64}"
    analyzer = analyzer or (
        MockFoodImageAnalyzer()
        if settings.food_image_provider == "mock"
        else LangChainLiteLLMFoodImageAnalyzer(settings)
    )
    if analyzer.provider != "mock":
        spent = db.scalar(
            select(func.coalesce(func.sum(AgentRun.estimated_cost_usd), 0)).where(
                AgentRun.created_at >= func.current_date()
            )
        )
        if Decimal(str(spent or 0)) >= Decimal(str(settings.food_image_daily_budget_usd)):
            raise APIError(
                status_code=429,
                code="food_image_daily_budget_exceeded",
                message="Daily food image budget is exhausted; use manual food entry",
            )

    run = AgentRun(
        user_id=user.id,
        request_id=request_id,
        status="running",
        input_hash=hashlib.sha256(f"food-image:{request_id}".encode()).hexdigest(),
        input_length=len(image_bytes),
        intents=["food_image"],
        provider=analyzer.provider,
        model=analyzer.model,
        prompt_version=FOOD_IMAGE_PROMPT_VERSION,
        schema_version=FOOD_IMAGE_SCHEMA_VERSION,
        knowledge_version=KNOWLEDGE_VERSION,
    )
    db.add(run)
    db.flush()
    started = time.perf_counter()
    invocation: FoodImageInvocation
    try:
        invocation = analyzer.analyze(
            data_url=data_url,
            note=payload.note,
            meal_type_hint=payload.meal_type_hint,
            scale_reference_type=payload.scale_reference_type,
            scale_reference_size_cm=payload.scale_reference_size_cm,
        )
    except (TimeoutError, ValueError, RuntimeError, OpenAIError) as error:
        invocation = FoodImageInvocation(
            output=None,
            provider=analyzer.provider,
            model=analyzer.model,
            input_tokens=0,
            output_tokens=0,
            latency_ms=int((time.perf_counter() - started) * 1000),
            estimated_cost_usd=0,
            fallback_used=True,
            error_code=(
                "invalid_structured_output"
                if isinstance(error, ValueError)
                else "provider_unavailable"
            ),
        )

    estimate = invocation.output
    candidate = None
    if estimate is not None and estimate.is_food:
        candidate_id, token = create_confirmation(db, user, run.id, "food")
        candidate = FoodAgentCandidate(
            kind="food",
            candidate_id=candidate_id,
            confirmation_token=token,
            payload=FoodRecordCreate(
                recorded_at=datetime.now(UTC),
                meal_type=estimate.meal_type,
                name=estimate.name or "待确认的一餐",
                energy_kcal=estimate.energy_kcal or 0,
                portion_amount=estimate.portion_amount,
                portion_unit=estimate.portion_unit,
                detail=(
                    f"图片估算区间 {estimate.energy_min_kcal:g}—{estimate.energy_max_kcal:g} kcal"
                    if estimate.energy_min_kcal is not None and estimate.energy_max_kcal is not None
                    else "图片估算，保存前请校正"
                ),
                source="image",
                source_ref=str(candidate_id),
            ),
            explanation=(
                "Mock 演示候选，未真实识别图片；请修改所有字段后再保存。"
                if invocation.provider == "mock"
                else "图片只生成估算候选；份量和热量存在误差，保存前必须校正。"
            ),
        )

    add_tool_trace(
        db,
        run_id=run.id,
        tool_name="food_image.analyze_candidate",
        started=started,
        status="completed" if candidate else "degraded",
        input_summary={
            "media_type": payload.media_type,
            "byte_length": len(image_bytes),
            "width": payload.width,
            "height": payload.height,
            "scale_reference_type": payload.scale_reference_type,
            "scale_reference_size_cm": payload.scale_reference_size_cm,
        },
        output_summary={
            "candidate_created": candidate is not None,
            "confidence": estimate.confidence if estimate else None,
            "scale_reference_used": estimate.scale_reference_used if estimate else False,
            "image_retained": False,
        },
        error_code=invocation.error_code,
        latency_ms=invocation.latency_ms,
    )
    run.status = "completed" if candidate else "degraded"
    run.provider = invocation.provider
    run.model = invocation.model
    run.input_tokens = invocation.input_tokens
    run.output_tokens = invocation.output_tokens
    run.latency_ms = invocation.latency_ms
    run.estimated_cost_usd = Decimal(str(invocation.estimated_cost_usd))
    run.fallback_used = invocation.fallback_used
    run.error_code = invocation.error_code
    run.completed_at = datetime.now(UTC)
    db.commit()
    return FoodImageAnalysisResponse(
        analysis_id=run.id,
        status="candidate" if candidate else "manual_required",
        candidate=candidate,
        estimate=estimate,
        message=(
            "已生成图片估算候选，请校正后确认保存。"
            if candidate
            else "无法可靠识别这张图片，请改用手动饮食记录。"
        ),
        fallback_used=invocation.fallback_used,
        usage=_usage(invocation),
    )
