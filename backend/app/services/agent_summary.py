import hashlib
import json
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.model_router import (
    KNOWLEDGE_VERSION,
    ModelRouter,
)
from app.agent.skills.journey_coach import (
    SKILL_NAME,
    SKILL_VERSION,
    SummaryPeriod,
    build_coach_signals,
    deterministic_coaching_content,
    requires_coaching_fallback,
)
from app.agent.tools import add_tool_trace
from app.api.errors import APIError
from app.knowledge.retriever import RetrievedChunk, retrieve
from app.models.agent import AgentRun, AgentSummaryCache
from app.models.user import User
from app.schemas.agent import (
    AgentCitation,
    AgentSummaryContent,
    AgentSummaryGenerated,
    AgentSummaryGoal,
    AgentSummaryPeriodStatistics,
    AgentSummaryResponse,
    AgentSummaryStatistics,
    AgentUsage,
)
from app.schemas.aggregates import JourneyDay
from app.services.agent_privacy import prepare_agent_access
from app.services.aggregates import journey
from app.services.profile import get_active_goal, get_profile

SUMMARY_PERIOD_DAYS = 30
RECENT_PERIOD_DAYS = 7
MINIMUM_RECORDED_DAYS: dict[SummaryPeriod, int] = {7: 2, 30: 7}
SUMMARY_PROMPT_VERSION = "journey-coach-summary-3.0.0"
SUMMARY_SCHEMA_VERSION = "journey-coach-summary-schema-3"


def _period_statistics(
    days: list[JourneyDay], *, period_days: int, start_date: date, end_date: date
) -> AgentSummaryPeriodStatistics:
    included = [item for item in days if start_date <= item.date <= end_date]
    food_count = sum(len(item.food_records) for item in included)
    activity_count = sum(len(item.activity_records) for item in included)
    weight_records = sorted(
        [record for item in included for record in item.weight_records],
        key=lambda record: (record.measured_at, str(record.id)),
    )
    weight_values = [float(record.weight_kg) for record in weight_records]
    return AgentSummaryPeriodStatistics(
        period_days=period_days,
        start_date=start_date,
        end_date=end_date,
        record_count=food_count + activity_count + len(weight_records),
        food_count=food_count,
        activity_count=activity_count,
        weight_count=len(weight_records),
        total_intake_kcal=round(sum(float(item.intake_kcal) for item in included), 2),
        total_activity_kcal=round(sum(float(item.activity_kcal) for item in included), 2),
        days_with_records=len(included),
        weight_change_kg=(
            round(weight_values[-1] - weight_values[0], 2) if len(weight_values) >= 2 else None
        ),
    )


def build_summary_context(
    db: Session, user: User
) -> tuple[AgentSummaryStatistics, list[JourneyDay]]:
    profile = get_profile(db, user)
    end_date = datetime.now(UTC).astimezone(ZoneInfo(profile.timezone)).date()
    start_30 = end_date - timedelta(days=SUMMARY_PERIOD_DAYS - 1)
    start_7 = end_date - timedelta(days=RECENT_PERIOD_DAYS - 1)
    records = journey(
        db,
        user,
        start_date=start_30,
        end_date=end_date,
        cursor=None,
        limit=SUMMARY_PERIOD_DAYS,
    )
    goal = get_active_goal(db, user.id)
    statistics = AgentSummaryStatistics(
        last_30_days=_period_statistics(
            records.items,
            period_days=SUMMARY_PERIOD_DAYS,
            start_date=start_30,
            end_date=end_date,
        ),
        last_7_days=_period_statistics(
            records.items,
            period_days=RECENT_PERIOD_DAYS,
            start_date=start_7,
            end_date=end_date,
        ),
        goal=(
            AgentSummaryGoal(
                kind=goal.kind,
                target_weight_kg=(
                    float(goal.target_weight_kg) if goal.target_weight_kg is not None else None
                ),
                daily_energy_target_kcal=(
                    float(goal.daily_energy_target_kcal)
                    if goal.daily_energy_target_kcal is not None
                    else None
                ),
            )
            if goal
            else None
        ),
    )
    return statistics, records.items


def _selected_period(
    statistics: AgentSummaryStatistics, period_days: SummaryPeriod
) -> AgentSummaryPeriodStatistics:
    return statistics.last_7_days if period_days == 7 else statistics.last_30_days


def _statistics_payload(
    statistics: AgentSummaryStatistics, period_days: SummaryPeriod
) -> dict[str, object]:
    payload: dict[str, object] = {
        "selected_period": _selected_period(statistics, period_days).model_dump(mode="json"),
        "goal": statistics.goal.model_dump(mode="json") if statistics.goal else None,
    }
    if period_days == 30:
        payload["last_7_days"] = statistics.last_7_days.model_dump(mode="json")
    return payload


def _fingerprint(
    statistics: AgentSummaryStatistics,
    coach_signals: dict[str, object],
    period_days: SummaryPeriod,
) -> str:
    payload = {
        "period_days": period_days,
        "prompt_version": SUMMARY_PROMPT_VERSION,
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "knowledge_version": KNOWLEDGE_VERSION,
        "statistics": _statistics_payload(statistics, period_days),
        "coach_signals": coach_signals,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _knowledge_query(statistics: AgentSummaryStatistics, period_days: SummaryPeriod) -> str | None:
    period = _selected_period(statistics, period_days)
    goal = statistics.goal
    # Short or sparse summaries are behavior coaching, not health education. Pulling
    # RAG into those requests adds latency without making the next action clearer.
    if period_days != 30 or goal is None or period.days_with_records < 14:
        return None
    if period.food_count == 0 and period.activity_count == 0:
        return None
    goal_topic = {
        "lose_fat": "减脂 均衡饮食 运动 恢复",
        "gain_muscle": "增肌 力量训练 饮食 恢复",
        "maintain": "体重维持 均衡饮食 运动 恢复",
    }[goal.kind]
    return f"{goal_topic} 习惯记录"


def _verified_citations(
    chunks: list[RetrievedChunk], cited_chunk_ids: list[str]
) -> list[AgentCitation]:
    allowed = {chunk.chunk_id: chunk for chunk in chunks if chunk.chunk_id}
    citations: list[AgentCitation] = []
    for chunk_id in dict.fromkeys(cited_chunk_ids):
        chunk = allowed.get(chunk_id)
        if chunk is None:
            continue
        citations.append(
            AgentCitation(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                source_slug=chunk.source_slug,
                title=chunk.title,
                source_url=chunk.source_url,
                version=chunk.version,
                region=chunk.region,
                score=chunk.score,
                excerpt=chunk.text[:300],
            )
        )
    return citations[:3]


def _prompt_payload(
    coach_signals: dict[str, object],
    chunks: list[RetrievedChunk],
    period_days: SummaryPeriod,
) -> str:
    return json.dumps(
        {
            "period": f"近{period_days}天",
            "coach_signals": coach_signals,
            "knowledge": [
                {
                    "chunk_id": chunk.chunk_id,
                    "title": chunk.title,
                    "version": chunk.version,
                    "text": chunk.text[:420],
                }
                for chunk in chunks
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _cached_response(
    cache: AgentSummaryCache, *, statistics: AgentSummaryStatistics, started: float
) -> AgentSummaryResponse:
    return AgentSummaryResponse(
        period_days=cache.period_days,
        generated_at=cache.generated_at,
        cache_hit=True,
        statistics=statistics,
        content=AgentSummaryContent.model_validate(cache.content),
        citations=[AgentCitation.model_validate(item) for item in cache.citations],
        fallback_used=cache.fallback_used,
        usage=AgentUsage(
            provider=cache.provider,
            model=cache.model,
            latency_ms=int((time.perf_counter() - started) * 1000),
        ),
    )


def generate_summary(
    db: Session,
    user: User,
    *,
    period_days: SummaryPeriod,
    request_id: str,
    model_router: ModelRouter | None = None,
) -> AgentSummaryResponse:
    started = time.perf_counter()
    statistics, summary_days = build_summary_context(db, user)
    selected_period = _selected_period(statistics, period_days)
    minimum_days = MINIMUM_RECORDED_DAYS[period_days]
    if selected_period.days_with_records < minimum_days:
        remaining_days = minimum_days - selected_period.days_with_records
        raise APIError(
            status_code=422,
            code="summary_insufficient_recorded_days",
            message=(
                f"近{period_days}天已有{selected_period.days_with_records}个有记录日；"
                f"再记录{remaining_days}天即可生成{period_days}天总结。"
            ),
            details={
                "period_days": period_days,
                "days_with_records": selected_period.days_with_records,
                "minimum_days_with_records": minimum_days,
                "remaining_days": remaining_days,
            },
        )
    coach_signals = build_coach_signals(summary_days, statistics, period_days)
    prepare_agent_access(db, user.id)
    fingerprint = _fingerprint(statistics, coach_signals, period_days)
    cache = db.scalar(
        select(AgentSummaryCache).where(
            AgentSummaryCache.user_id == user.id,
            AgentSummaryCache.period_days == period_days,
        )
    )
    if cache is not None and cache.fingerprint == fingerprint:
        cache.statistics = statistics.model_dump(mode="json")
        db.commit()
        return _cached_response(cache, statistics=statistics, started=started)

    router = model_router or ModelRouter(db)
    router.bind_user(user.id)
    run = AgentRun(
        user_id=user.id,
        request_id=request_id,
        status="running",
        input_hash=fingerprint,
        input_length=len(json.dumps(coach_signals, ensure_ascii=False)),
        intents=["weekly_summary"],
        plan={
            "kind": f"{period_days}_day_summary",
            "skill": f"{SKILL_NAME}@{SKILL_VERSION}",
            "llm_calls": 1,
        },
        verification={},
        provider=router.provider,
        model=router.model_for("thirty_day_summary"),
        prompt_version=SUMMARY_PROMPT_VERSION,
        schema_version=SUMMARY_SCHEMA_VERSION,
        knowledge_version=KNOWLEDGE_VERSION,
    )
    db.add(run)
    db.flush()
    add_tool_trace(
        db,
        run_id=run.id,
        tool_name=f"{'weekly' if period_days == 7 else 'monthly'}_summary.statistics",
        started=started,
        input_summary={"period_days": period_days},
        output_summary={
            "record_count_30d": statistics.last_30_days.record_count,
            "record_count_7d": statistics.last_7_days.record_count,
            "days_with_records_30d": statistics.last_30_days.days_with_records,
            "coach_skill": f"{SKILL_NAME}@{SKILL_VERSION}",
        },
    )

    retrieve_started = time.perf_counter()
    query = _knowledge_query(statistics, period_days)
    chunks = retrieve(db, query, limit=3, minimum_score=0.1) if query else []
    add_tool_trace(
        db,
        run_id=run.id,
        tool_name=f"{'weekly' if period_days == 7 else 'monthly'}_summary.retrieve",
        started=retrieve_started,
        status="completed" if query else "skipped",
        input_summary={"conditional": True, "query_present": bool(query)},
        output_summary={"chunk_count": len(chunks)},
    )

    generate_started = time.perf_counter()
    invocation = router.generate(
        "thirty_day_summary",
        AgentSummaryGenerated,
        system_prompt=(
            f"你是 Journey 的近{period_days}天行为教练。后端已经完成所有统计，禁止自行计算、改写或"
            "猜测数值。每条发现必须分别写清结论、证据和含义；每条行动必须写清具体计划、"
            "原因和带数字的7天验收标准。禁止把输入统计原样复述成建议。"
            f"主周期必须始终写近{period_days}天；引用其他周期指标时必须明确标注周期。"
            "数据覆盖不足时要明确提醒不要据此减少热量，但仍需给出记录、运动或称重行动。"
            "达到生成门槛后不得使用无法评估作为结论。不要写大段科普、"
            "诊断、处方或保证结果。只有确实使用提供的知识片段时才返回对应真实 chunk_id；"
            "没有使用则返回空列表。"
        ),
        user_prompt=_prompt_payload(coach_signals, chunks, period_days),
        fallback_factory=lambda: deterministic_coaching_content(
            statistics, coach_signals, period_days
        ),
        max_retries=0,
    )
    generated = AgentSummaryGenerated.model_validate(invocation.output)
    period_guard_fallback = requires_coaching_fallback(generated, period_days)
    if period_guard_fallback:
        generated = deterministic_coaching_content(statistics, coach_signals, period_days)
    citations = _verified_citations(chunks, generated.cited_chunk_ids)
    content = AgentSummaryContent(
        headline=generated.headline,
        key_findings=generated.key_findings,
        next_7_days=generated.next_7_days,
    )
    add_tool_trace(
        db,
        run_id=run.id,
        tool_name=f"{'weekly' if period_days == 7 else 'monthly'}_summary.generate",
        started=generate_started,
        status="failed" if invocation.error_code else "completed",
        input_summary={
            "structured_statistics": True,
            "raw_records_sent": 0,
            "knowledge_chunk_count": len(chunks),
            "llm_call_count": 1,
        },
        output_summary={
            "finding_count": len(content.key_findings),
            "suggestion_count": len(content.next_7_days),
            "citation_count": len(citations),
            "period_guard_fallback": period_guard_fallback,
        },
        error_code=invocation.error_code,
        latency_ms=invocation.latency_ms,
    )

    generated_at = datetime.now(UTC)
    if cache is None:
        cache = AgentSummaryCache(user_id=user.id, period_days=period_days)
        db.add(cache)
    cache.fingerprint = fingerprint
    cache.statistics = statistics.model_dump(mode="json")
    cache.content = content.model_dump(mode="json")
    cache.citations = [item.model_dump(mode="json") for item in citations]
    cache.provider = invocation.provider
    cache.model = invocation.model
    cache.fallback_used = invocation.fallback_used or period_guard_fallback
    cache.generated_at = generated_at

    run.status = "degraded" if invocation.error_code else "completed"
    run.provider = invocation.provider
    run.model = invocation.model
    run.input_tokens = invocation.input_tokens
    run.output_tokens = invocation.output_tokens
    run.retries = invocation.retries
    run.estimated_cost_usd = Decimal(str(invocation.estimated_cost_usd))
    run.fallback_used = invocation.fallback_used or period_guard_fallback
    run.error_code = invocation.error_code
    run.latency_ms = int((time.perf_counter() - started) * 1000)
    run.completed_at = generated_at
    db.commit()

    return AgentSummaryResponse(
        period_days=period_days,
        generated_at=generated_at,
        cache_hit=False,
        statistics=statistics,
        content=content,
        citations=citations,
        fallback_used=invocation.fallback_used or period_guard_fallback,
        usage=AgentUsage(
            provider=invocation.provider,
            model=invocation.model,
            input_tokens=invocation.input_tokens,
            output_tokens=invocation.output_tokens,
            retries=invocation.retries,
            latency_ms=run.latency_ms,
            estimated_cost_usd=invocation.estimated_cost_usd,
        ),
    )
