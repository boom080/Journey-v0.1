import hashlib
import re
import time
import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.agent.model_router import ModelInvocation, ModelRouter
from app.core.security import create_agent_confirmation_token
from app.models.agent import AgentConfirmation, AgentToolRun
from app.models.user import User
from app.schemas.agent import (
    ActivityAgentCandidate,
    ActivityParsed,
    AgentCandidate,
    FoodAgentCandidate,
    FoodParsed,
    WeightAgentCandidate,
    WeightParsed,
)
from app.schemas.records import ActivityRecordCreate, FoodRecordCreate, WeightRecordCreate
from app.services.aggregates import journey
from app.services.profile import get_profile


def _food_fallback(text: str) -> FoodParsed:
    meal_type = (
        "breakfast"
        if "早餐" in text
        else "lunch"
        if "午餐" in text
        else "dinner"
        if "晚餐" in text
        else "snack"
        if "加餐" in text or "夜宵" in text
        else "other"
    )
    energy = (
        float(re.search(r"(\d+(?:\.\d+)?)\s*(?:千卡|大卡|kcal)", text, re.I).group(1))
        if re.search(r"(\d+(?:\.\d+)?)\s*(?:千卡|大卡|kcal)", text, re.I)
        else 300
    )
    name = re.sub(r"^(?:我)?(?:早餐|午餐|晚餐|加餐|夜宵)?(?:吃了|喝了|吃|喝)?", "", text).strip(
        " ，,"
    )
    name = re.sub(r"\d+(?:\.\d+)?\s*(?:千卡|大卡|kcal)", "", name, flags=re.I).strip(" ，,")
    return FoodParsed(meal_type=meal_type, name=name[:120] or "一份食物", energy_kcal=energy)


def _food_meal_type(text: str, parsed_meal_type: str, local_hour: int) -> str:
    explicit = (
        "breakfast"
        if re.search(r"(早餐|早饭)", text)
        else "lunch"
        if re.search(r"(午餐|午饭)", text)
        else "dinner"
        if re.search(r"(晚餐|晚饭)", text)
        else "snack"
        if re.search(r"(加餐|夜宵)", text)
        else None
    )
    if explicit is not None:
        return explicit
    if 5 <= local_hour < 10:
        return "breakfast"
    if 10 <= local_hour < 15:
        return "lunch"
    if 15 <= local_hour < 17:
        return "snack"
    if 17 <= local_hour < 22:
        return "dinner"
    return parsed_meal_type


def _default_food_portion(name: str) -> tuple[float, str]:
    if re.search(r"(面|粉|饭|粥|汤|羹|馄饨|抄手|麻辣烫)", name):
        return 1, "碗"
    if re.search(r"(水|茶|咖啡|奶|果汁|饮料)", name):
        return 1, "杯"
    return 1, "份"


def _activity_fallback(text: str) -> ActivityParsed:
    duration_match = re.search(r"(\d+)\s*(?:分钟|min)", text, re.I)
    energy_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:千卡|大卡|kcal)", text, re.I)
    duration = int(duration_match.group(1)) if duration_match else 30
    energy = float(energy_match.group(1)) if energy_match else max(80, duration * 6)
    intensity = (
        "high"
        if re.search(r"(高强度|冲刺|剧烈)", text)
        else "low"
        if re.search(r"(低强度|散步|舒缓)", text)
        else "moderate"
    )
    name = re.sub(r"\d+(?:\.\d+)?\s*(?:分钟|min|千卡|大卡|kcal)", "", text, flags=re.I).strip(
        " ，,"
    )
    return ActivityParsed(
        name=name[:120] or "运动",
        duration_minutes=duration,
        intensity=intensity,
        energy_kcal=energy,
    )


def _weight_fallback(text: str) -> WeightParsed:
    match = re.search(r"(?:体重|称重|称了)\s*(?:是|为)?\s*(\d{2,3}(?:\.\d+)?)", text)
    if match is None:
        raise ValueError("weight_value_missing")
    return WeightParsed(weight_kg=float(match.group(1)))


def create_confirmation(
    db: Session,
    user: User,
    run_id: uuid.UUID,
    kind: str,
    *,
    step_id: str | None = None,
) -> tuple[uuid.UUID, str]:
    candidate_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    token = create_agent_confirmation_token(
        user_id=user.id,
        run_id=run_id,
        candidate_id=candidate_id,
        kind=kind,
        expires_at=expires_at,
    )
    db.add(
        AgentConfirmation(
            candidate_id=candidate_id,
            run_id=run_id,
            user_id=user.id,
            kind=kind,
            step_id=step_id,
            token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            expires_at=expires_at,
        )
    )
    return candidate_id, token


def build_write_candidate(
    db: Session,
    user: User,
    run_id: uuid.UUID,
    intent: str,
    text: str,
    model_router: ModelRouter,
    *,
    step_id: str | None = None,
) -> tuple[AgentCandidate, ModelInvocation]:
    if intent == "food":
        recorded_at = datetime.now(UTC)
        invocation = model_router.generate(
            "food_text_parse",
            FoodParsed,
            system_prompt=(
                "解析饮食为结构化候选，不执行写入。用户未说明餐别时可返回 other；"
                "用户未说明份量时给出合理的常见单份估算。"
            ),
            user_prompt=text,
            fallback_factory=lambda: _food_fallback(text),
        )
        parsed = FoodParsed.model_validate(invocation.output)
        default_amount, default_unit = _default_food_portion(parsed.name)
        portion_amount = parsed.portion_amount or default_amount
        portion_unit = parsed.portion_unit or (
            "克"
            if parsed.portion_amount is not None and parsed.portion_amount > 10
            else default_unit
        )
        meal_type = _food_meal_type(
            text,
            parsed.meal_type,
            recorded_at.astimezone(ZoneInfo(user.profile.timezone)).hour,
        )
        candidate_id, token = create_confirmation(db, user, run_id, intent, step_id=step_id)
        return FoodAgentCandidate(
            kind="food",
            candidate_id=candidate_id,
            confirmation_token=token,
            payload=FoodRecordCreate(
                recorded_at=recorded_at,
                meal_type=meal_type,
                name=parsed.name,
                energy_kcal=parsed.energy_kcal,
                portion_amount=portion_amount,
                portion_unit=portion_unit,
                source="agent",
                source_ref=str(candidate_id),
            ),
            explanation="已填入默认餐别、份量和热量估算；确认后可在 Journey 编辑。",
        ), invocation
    if intent == "activity":
        invocation = model_router.generate(
            "activity_text_parse",
            ActivityParsed,
            system_prompt="解析运动为结构化候选，不执行写入。",
            user_prompt=text,
            fallback_factory=lambda: _activity_fallback(text),
        )
        parsed = ActivityParsed.model_validate(invocation.output)
        candidate_id, token = create_confirmation(db, user, run_id, intent, step_id=step_id)
        return ActivityAgentCandidate(
            kind="activity",
            candidate_id=candidate_id,
            confirmation_token=token,
            payload=ActivityRecordCreate(
                recorded_at=datetime.now(UTC),
                name=parsed.name,
                activity_type=parsed.name,
                duration_minutes=parsed.duration_minutes,
                intensity=parsed.intensity,
                energy_kcal=parsed.energy_kcal,
                source="agent",
                source_ref=str(candidate_id),
            ),
            explanation="Agent 只生成候选；消耗为估算值，保存前可修改。",
        ), invocation
    invocation = model_router.generate(
        "weight_text_parse",
        WeightParsed,
        system_prompt="解析体重为结构化候选，不执行写入。",
        user_prompt=text,
        fallback_factory=lambda: _weight_fallback(text),
    )
    parsed = WeightParsed.model_validate(invocation.output)
    candidate_id, token = create_confirmation(db, user, run_id, intent, step_id=step_id)
    return WeightAgentCandidate(
        kind="weight",
        candidate_id=candidate_id,
        confirmation_token=token,
        payload=WeightRecordCreate(
            measured_at=datetime.now(UTC), weight_kg=parsed.weight_kg, source="agent"
        ),
        explanation="Agent 只生成候选；保存前请核对称重数值。",
    ), invocation


def add_tool_trace(
    db: Session,
    *,
    run_id: uuid.UUID,
    tool_name: str,
    started: float,
    status: str = "completed",
    input_summary: dict | None = None,
    output_summary: dict | None = None,
    error_code: str | None = None,
    latency_ms: int | None = None,
) -> None:
    db.add(
        AgentToolRun(
            run_id=run_id,
            tool_name=tool_name,
            status=status,
            input_summary=input_summary or {},
            output_summary=output_summary or {},
            latency_ms=(
                latency_ms
                if latency_ms is not None
                else int((time.perf_counter() - started) * 1000)
            ),
            error_code=error_code,
        )
    )


def read_profile_tool(db: Session, user: User) -> dict:
    return get_profile(db, user).model_dump(mode="json")


def read_journey_tool(db: Session, user: User, days: int = 7) -> dict:
    return journey(db, user, start_date=None, end_date=None, cursor=None, limit=days).model_dump(
        mode="json"
    )
