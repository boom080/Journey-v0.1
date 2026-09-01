import json
import time
from dataclasses import dataclass, replace
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agent.context import ContextSnapshot, build_context
from app.agent.model_router import ModelInvocation, ModelRouter
from app.knowledge.retriever import RetrievedChunk, retrieve
from app.models.user import User
from app.schemas.agent import (
    AgentCitation,
    KnowledgeGenerated,
    RecommendationGenerated,
    WeeklySummaryGenerated,
)


class WorkflowState(TypedDict, total=False):
    context: ContextSnapshot
    chunks: list[RetrievedChunk]
    answer: str
    cited_chunk_ids: list[str]
    invocation: ModelInvocation


@dataclass(frozen=True)
class WorkflowResult:
    answer: str
    citations: list[AgentCitation]
    invocation: ModelInvocation
    context: ContextSnapshot | None
    node_traces: list[dict]


_INSUFFICIENT_CONTEXT_ANSWER = (
    "insufficient_context：受控知识库中没有足够相关资料。你可以改写问题，或咨询合格专业人员。"
)
_CITATION_VERIFICATION_ERROR = "citation_verification_failed"


def _has_valid_chunk_id(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _citations(chunks: list[RetrievedChunk], cited_ids: list[str]) -> list[AgentCitation]:
    allowed = {
        chunk.chunk_id: chunk
        for chunk in chunks
        if _has_valid_chunk_id(getattr(chunk, "chunk_id", None))
    }
    citations: list[AgentCitation] = []
    for item in cited_ids:
        chunk = allowed.get(item)
        if chunk is None:
            continue
        try:
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
        except (AttributeError, TypeError, ValueError):
            continue
    return citations


def run_knowledge(
    db: Session,
    model_router: ModelRouter,
    question: str,
    *,
    chunks_override: list[RetrievedChunk] | None = None,
) -> WorkflowResult:
    started = time.perf_counter()
    chunks = chunks_override if chunks_override is not None else retrieve(db, question)
    node_traces = [
        {
            "name": "knowledge.retrieve",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "output_summary": {"chunk_count": len(chunks)},
        }
    ]

    if not chunks:
        output = KnowledgeGenerated(answer=_INSUFFICIENT_CONTEXT_ANSWER)
        invocation = ModelInvocation(
            output=output,
            provider=model_router.provider,
            model=model_router.model_for("knowledge_answer"),
            input_tokens=0,
            output_tokens=0,
            retries=0,
            latency_ms=0,
            estimated_cost_usd=0,
            fallback_used=False,
            error_code="insufficient_context",
        )
        node_traces.append(
            {
                "name": "knowledge.generate",
                "latency_ms": 0,
                "output_summary": {
                    "citation_count": 0,
                    "generation_skipped": "insufficient_context",
                },
                "error_code": None,
            }
        )
        return WorkflowResult(output.answer, [], invocation, None, node_traces)

    def fallback() -> KnowledgeGenerated:
        fallback_chunk = next(
            (chunk for chunk in chunks if _has_valid_chunk_id(getattr(chunk, "chunk_id", None))),
            None,
        )
        if fallback_chunk is None:
            return KnowledgeGenerated(answer=_INSUFFICIENT_CONTEXT_ANSWER)

        answer = getattr(fallback_chunk, "text", None)
        if not isinstance(answer, str) or not answer:
            answer = _INSUFFICIENT_CONTEXT_ANSWER
        else:
            answer = answer[:1200]
        if any(word in question for word in ("疾病", "药", "处方", "胸痛", "晕厥", "孕期")):
            answer = (
                "这个问题可能涉及医疗判断。Journey 不提供诊断或治疗建议；请优先咨询合格专业人员。"
            )
        return KnowledgeGenerated(answer=answer, cited_chunk_ids=[fallback_chunk.chunk_id])

    started = time.perf_counter()
    invocation = model_router.generate(
        "knowledge_answer",
        KnowledgeGenerated,
        system_prompt=(
            "只依据提供的受控知识片段回答并列出真实 chunk id。没有证据时明确 no-answer；"
            "不提供医疗诊断或处方。"
        ),
        user_prompt=json.dumps(
            {"question": question, "chunks": [chunk.__dict__ for chunk in chunks]},
            ensure_ascii=False,
        ),
        fallback_factory=fallback,
    )
    generated = KnowledgeGenerated.model_validate(invocation.output)
    citations = _citations(chunks, generated.cited_chunk_ids)
    citation_fallback_used = False
    citation_verification_failed = False
    if not citations:
        fallback_output = fallback()
        generated = fallback_output
        citations = _citations(chunks, fallback_output.cited_chunk_ids)
        citation_fallback_used = True
        if not citations:
            generated = KnowledgeGenerated(answer=_INSUFFICIENT_CONTEXT_ANSWER)
            invocation = replace(
                invocation,
                fallback_used=True,
                error_code=_CITATION_VERIFICATION_ERROR,
            )
            citation_verification_failed = True
        else:
            invocation = replace(invocation, fallback_used=True)
    node_traces.append(
        {
            "name": "knowledge.generate",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "output_summary": {
                "citation_count": len(citations),
                "citation_fallback_used": citation_fallback_used,
                "citation_verification": "failed" if citation_verification_failed else "passed",
            },
            "error_code": (
                _CITATION_VERIFICATION_ERROR
                if citation_verification_failed
                else invocation.error_code
            ),
        }
    )
    return WorkflowResult(generated.answer, citations, invocation, None, node_traces)


def _run_graph(
    db: Session,
    user: User,
    model_router: ModelRouter,
    *,
    capability: str,
    context_override: ContextSnapshot | None = None,
    chunks_override: list[RetrievedChunk] | None = None,
) -> WorkflowResult:
    graph = StateGraph(WorkflowState)
    node_traces: list[dict] = []

    def context_node(state: WorkflowState) -> WorkflowState:
        started = time.perf_counter()
        context = context_override or build_context(db, user)
        node_traces.append(
            {
                "name": f"{capability}.context",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "output_summary": {
                    "context_version": context.version,
                    "estimated_tokens": context.estimated_tokens,
                },
            }
        )
        return {"context": context}

    def retrieve_node(state: WorkflowState) -> WorkflowState:
        started = time.perf_counter()
        query = (
            "均衡饮食 运动恢复 睡眠 安全"
            if capability == "recommendation"
            else "每周健康记录 饮食 运动 恢复"
        )
        chunks = (
            chunks_override
            if chunks_override is not None
            else retrieve(db, query, limit=3, minimum_score=0.1)
        )
        node_traces.append(
            {
                "name": f"{capability}.retrieve",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "output_summary": {"chunk_count": len(chunks)},
            }
        )
        return {"chunks": chunks}

    def generate_node(state: WorkflowState) -> WorkflowState:
        started = time.perf_counter()
        context = state["context"]
        chunks = state["chunks"]
        schema = (
            RecommendationGenerated if capability == "recommendation" else WeeklySummaryGenerated
        )

        def fallback():
            today = context.data["today"]
            recent = context.data.get("recent_totals", {})
            if capability == "recommendation":
                goal = context.data.get("goal")
                goal_text = f"当前目标为 {goal['kind']}。" if goal else "尚未设置明确目标。"
                summary = (
                    f"{goal_text} 今日摄入 {today['intake_kcal']} kcal、"
                    f"运动 {today['activity_kcal']} kcal。"
                    "建议先保持可执行的小调整：规律记录、安排恢复，并根据实际饥饿和训练状态复盘。"
                )
                return RecommendationGenerated(
                    summary=summary,
                    cited_chunk_ids=[chunk.chunk_id for chunk in chunks[:2]],
                )
            weight_change = recent.get("weight_change_kg")
            weight_sentence = (
                f"体重变化 {weight_change} kg。"
                if weight_change is not None
                else "体重记录不足，暂不判断变化。"
            )
            summary = (
                f"近 {recent.get('range_days', 7)} 天记录覆盖 "
                f"{recent.get('days_with_records', 0)} 天，"
                f"饮食 {recent.get('food_count', 0)} 条、"
                f"运动 {recent.get('activity_count', 0)} 条、"
                f"体重 {recent.get('weight_count', 0)} 条；"
                f"累计摄入 {recent.get('intake_kcal', 0)} kcal，"
                f"运动消耗 {recent.get('activity_kcal', 0)} kcal。"
                + (
                    f"静息消耗估算 {recent.get('resting_energy_kcal_per_day')} kcal/天，"
                    f"扣除静息与已记录运动后的记录口径估算余量 "
                    f"{recent.get('estimated_energy_balance_kcal')} kcal；"
                    "该值不等于 TDEE，漏记饮食也会使结果失真。"
                    if recent.get("resting_energy_kcal_per_day") is not None
                    else f"静息消耗暂不可估算：{recent.get('energy_estimate_note', '画像信息不足')}"
                )
                + weight_sentence
                + "这是基于结构化数据的确定性总结，可继续观察记录完整性和趋势。"
            )
            return WeeklySummaryGenerated(
                summary=summary,
                cited_chunk_ids=[chunk.chunk_id for chunk in chunks[:2]],
            )

        invocation = model_router.generate(
            capability,
            schema,
            system_prompt=(
                "基于最小必要结构化画像、确定性聚合和受控知识生成结果；必须使用真实 chunk id；"
                "不诊断疾病，不静默修改画像。"
            ),
            user_prompt=json.dumps(
                {
                    "context_version": context.version,
                    "context": context.data,
                    "chunks": [chunk.__dict__ for chunk in chunks],
                },
                ensure_ascii=False,
            ),
            fallback_factory=fallback,
        )
        generated = schema.model_validate(invocation.output)
        allowed_ids = {chunk.chunk_id for chunk in chunks}
        if chunks and (
            not generated.cited_chunk_ids
            or any(item not in allowed_ids for item in generated.cited_chunk_ids)
        ):
            generated = fallback()
        node_traces.append(
            {
                "name": f"{capability}.generate",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "output_summary": {"citation_count": len(generated.cited_chunk_ids)},
                "error_code": invocation.error_code,
            }
        )
        return {
            "answer": generated.summary,
            "cited_chunk_ids": generated.cited_chunk_ids,
            "invocation": invocation,
        }

    graph.add_node("context", context_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_edge(START, "context")
    graph.add_edge("context", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    result = graph.compile().invoke({})
    chunks = result["chunks"]
    citations = _citations(chunks, result["cited_chunk_ids"])
    return WorkflowResult(
        answer=result["answer"],
        citations=citations,
        invocation=result["invocation"],
        context=result["context"],
        node_traces=node_traces,
    )


def run_recommendation(
    db: Session,
    user: User,
    model_router: ModelRouter,
    *,
    context: ContextSnapshot | None = None,
    chunks: list[RetrievedChunk] | None = None,
) -> WorkflowResult:
    return _run_graph(
        db,
        user,
        model_router,
        capability="recommendation",
        context_override=context,
        chunks_override=chunks,
    )


def run_weekly_summary(
    db: Session,
    user: User,
    model_router: ModelRouter,
    *,
    context: ContextSnapshot | None = None,
    chunks: list[RetrievedChunk] | None = None,
) -> WorkflowResult:
    return _run_graph(
        db,
        user,
        model_router,
        capability="weekly_summary",
        context_override=context,
        chunks_override=chunks,
    )
