import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.agent.context import ContextSnapshot, build_context
from app.agent.model_router import ModelInvocation, ModelRouter
from app.agent.specialists import SPECIALIST_REGISTRY, specialist_for_tool
from app.agent.tools import build_write_candidate, read_journey_tool, read_profile_tool
from app.agent.workflows import run_knowledge, run_recommendation, run_weekly_summary
from app.knowledge.retriever import RetrievedChunk, retrieve
from app.models.user import User
from app.schemas.agent import AgentCandidate, AgentCitation, AgentPlanStep, AgentToolName

ToolRisk = Literal["read", "generate", "confirmation_required"]
ToolStatus = Literal["completed", "failed", "skipped", "awaiting_confirmation"]


@dataclass(frozen=True)
class ToolSpec:
    name: AgentToolName
    description: str
    risk: ToolRisk
    requires_confirmation: bool
    read_only: bool
    recovery_tools: tuple[AgentToolName, ...] = ()


@dataclass
class ToolRuntime:
    db: Session
    user: User
    run_id: uuid.UUID
    model_router: ModelRouter
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecution:
    step_id: str
    tool: AgentToolName
    status: ToolStatus
    message: str
    latency_ms: int
    answer: str | None = None
    candidates: list[AgentCandidate] = field(default_factory=list)
    citations: list[AgentCitation] = field(default_factory=list)
    invocations: list[ModelInvocation] = field(default_factory=list)
    output_summary: dict[str, Any] = field(default_factory=dict)
    node_traces: list[dict] = field(default_factory=list)
    error_code: str | None = None
    specialist: str = "orchestrator"


TOOL_REGISTRY: dict[AgentToolName, ToolSpec] = {
    "context.load": ToolSpec(
        "context.load", "加载最小必要画像、目标和近期聚合", "read", False, True
    ),
    "profile.read": ToolSpec("profile.read", "读取当前用户画像", "read", False, True),
    "journey.read": ToolSpec("journey.read", "读取近期 Journey", "read", False, True),
    "food.parse_candidate": ToolSpec(
        "food.parse_candidate", "解析饮食并生成待确认候选", "confirmation_required", True, True
    ),
    "activity.parse_candidate": ToolSpec(
        "activity.parse_candidate", "解析运动并生成待确认候选", "confirmation_required", True, True
    ),
    "weight.parse_candidate": ToolSpec(
        "weight.parse_candidate", "解析体重并生成待确认候选", "confirmation_required", True, True
    ),
    "knowledge.answer": ToolSpec(
        "knowledge.answer",
        "检索受控知识并回答",
        "generate",
        False,
        True,
        ("knowledge.safe_summary",),
    ),
    "knowledge.retrieve": ToolSpec(
        "knowledge.retrieve", "为个性化工作流检索受控知识", "read", False, True
    ),
    "recommendation.generate": ToolSpec(
        "recommendation.generate",
        "基于上下文和知识生成建议",
        "generate",
        False,
        True,
        ("recommendation.rules_fallback",),
    ),
    "weekly_summary.generate": ToolSpec(
        "weekly_summary.generate", "基于上下文和知识生成周总结", "generate", False, True
    ),
    "knowledge.safe_summary": ToolSpec(
        "knowledge.safe_summary", "在模型失败时返回检索证据摘要", "read", False, True
    ),
    "recommendation.rules_fallback": ToolSpec(
        "recommendation.rules_fallback", "在模型失败时返回规则化安全建议", "read", False, True
    ),
}


def public_tool_catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "risk": spec.risk,
            "requires_confirmation": spec.requires_confirmation,
            "specialist": specialist_for_tool(spec.name),
        }
        for spec in TOOL_REGISTRY.values()
    ]


def _candidate_summary(candidate: AgentCandidate) -> dict[str, Any]:
    if candidate.kind == "food":
        return {
            "kind": "food",
            "candidate_count": 1,
            "energy_present": candidate.payload.energy_kcal is not None,
        }
    if candidate.kind == "activity":
        return {
            "kind": "activity",
            "candidate_count": 1,
            "duration_present": candidate.payload.duration_minutes is not None,
        }
    return {"kind": "weight", "candidate_count": 1, "value_present": True}


def _summary_range_days(segment: str | None) -> int:
    value = segment or ""
    return 30 if re.search(r"(30\s*天|一个月|本月|月总结|月趋势)", value) else 7


def _execute(runtime: ToolRuntime, step: AgentPlanStep) -> ToolExecution:
    started = time.perf_counter()
    tool = step.tool
    if tool == "context.load":
        context = build_context(
            runtime.db,
            runtime.user,
            range_days=_summary_range_days(step.segment),
        )
        runtime.artifacts["context"] = context
        return ToolExecution(
            step.id,
            tool,
            "completed",
            "已加载最小必要用户上下文",
            int((time.perf_counter() - started) * 1000),
            output_summary={
                "context_version": context.version,
                "data_range_days": context.data.get("range_days", 7),
                "estimated_tokens": context.estimated_tokens,
                "sources": context.included_sources,
            },
        )
    if tool == "profile.read":
        profile = read_profile_tool(runtime.db, runtime.user)
        runtime.artifacts[tool] = profile
        return ToolExecution(
            step.id,
            tool,
            "completed",
            "已读取当前用户画像",
            int((time.perf_counter() - started) * 1000),
            answer=(
                f"你的当前画像昵称是 {profile['display_name']}，"
                f"最新体重为 {profile.get('latest_weight_kg') or '未记录'} kg。"
            ),
            output_summary={"profile_available": True},
        )
    if tool == "journey.read":
        history = read_journey_tool(runtime.db, runtime.user)
        runtime.artifacts[tool] = history
        return ToolExecution(
            step.id,
            tool,
            "completed",
            "已读取近期 Journey",
            int((time.perf_counter() - started) * 1000),
            answer=f"最近返回 {len(history['items'])} 个有记录的日期，可在 Journey 查看明细。",
            output_summary={"days_returned": len(history["items"])},
        )
    if tool in {
        "food.parse_candidate",
        "activity.parse_candidate",
        "weight.parse_candidate",
    }:
        intent = tool.split(".", maxsplit=1)[0]
        candidate, invocation = build_write_candidate(
            runtime.db,
            runtime.user,
            runtime.run_id,
            intent,
            step.segment or "",
            runtime.model_router,
            step_id=step.id,
        )
        return ToolExecution(
            step.id,
            tool,
            "awaiting_confirmation",
            "已生成候选，等待用户确认后写入",
            int((time.perf_counter() - started) * 1000),
            candidates=[candidate],
            invocations=[invocation],
            output_summary=_candidate_summary(candidate),
        )
    if tool == "knowledge.answer":
        result = run_knowledge(runtime.db, runtime.model_router, step.segment or "")
        if result.invocation.error_code not in {None, "insufficient_context"}:
            return ToolExecution(
                step.id,
                tool,
                "failed",
                "知识生成模型失败，准备切换到受控证据摘要",
                int((time.perf_counter() - started) * 1000),
                invocations=[result.invocation],
                output_summary={"citation_count": len(result.citations)},
                node_traces=result.node_traces,
                error_code=result.invocation.error_code,
            )
        return ToolExecution(
            step.id,
            tool,
            "completed",
            "已完成受控知识检索与回答",
            int((time.perf_counter() - started) * 1000),
            answer=result.answer,
            citations=result.citations,
            invocations=[result.invocation],
            output_summary={
                "citation_count": len(result.citations),
                "insufficient_context": result.invocation.error_code == "insufficient_context",
            },
            node_traces=result.node_traces,
        )
    if tool == "knowledge.retrieve":
        query = step.segment or "均衡饮食 运动恢复 睡眠 安全"
        chunks = retrieve(runtime.db, query, limit=3, minimum_score=0.1)
        runtime.artifacts[tool] = chunks
        return ToolExecution(
            step.id,
            tool,
            "completed",
            "已检索受控健康知识",
            int((time.perf_counter() - started) * 1000),
            output_summary={
                "chunk_count": len(chunks),
                "retrieved_documents": list(dict.fromkeys(chunk.document_id for chunk in chunks)),
                "retrieval_score": max((chunk.score for chunk in chunks), default=0),
            },
        )
    if tool in {"recommendation.generate", "weekly_summary.generate"}:
        context = runtime.artifacts.get("context")
        chunks = runtime.artifacts.get("knowledge.retrieve")
        if context is not None and not isinstance(context, ContextSnapshot):
            raise ValueError("invalid_context_artifact")
        if chunks is not None and not all(isinstance(item, RetrievedChunk) for item in chunks):
            raise ValueError("invalid_knowledge_artifact")
        result = (
            run_recommendation(
                runtime.db,
                runtime.user,
                runtime.model_router,
                context=context,
                chunks=chunks,
            )
            if tool == "recommendation.generate"
            else run_weekly_summary(
                runtime.db,
                runtime.user,
                runtime.model_router,
                context=context,
                chunks=chunks,
            )
        )
        if result.invocation.error_code:
            return ToolExecution(
                step.id,
                tool,
                "failed",
                "生成模型失败，准备执行确定性降级工具",
                int((time.perf_counter() - started) * 1000),
                invocations=[result.invocation],
                output_summary={"citation_count": len(result.citations)},
                node_traces=result.node_traces,
                error_code=result.invocation.error_code,
            )
        return ToolExecution(
            step.id,
            tool,
            "completed",
            "已基于上下文和受控知识生成结果",
            int((time.perf_counter() - started) * 1000),
            answer=result.answer,
            citations=result.citations,
            invocations=[result.invocation],
            output_summary={"citation_count": len(result.citations)},
            node_traces=result.node_traces,
        )
    if tool == "knowledge.safe_summary":
        chunks = runtime.artifacts.get("knowledge.retrieve")
        if not chunks:
            chunks = retrieve(runtime.db, step.segment or "饮食 运动 恢复 安全", limit=2)
        citations = [
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
            for chunk in chunks[:2]
        ]
        answer = (
            "受控知识库暂时没有足够相关资料，请换一种问法。"
            if not chunks
            else "模型暂时不可用。以下是受控知识库中的直接摘要：" + chunks[0].text[:600]
        )
        return ToolExecution(
            step.id,
            tool,
            "completed",
            "已切换到受控知识摘要",
            int((time.perf_counter() - started) * 1000),
            answer=answer,
            citations=citations,
            output_summary={"citation_count": len(citations), "deterministic": True},
        )
    if tool == "recommendation.rules_fallback":
        context = runtime.artifacts.get("context") or build_context(runtime.db, runtime.user)
        today = context.data["today"]
        goal = context.data.get("goal")
        goal_text = f"当前目标为 {goal['kind']}。" if goal else "尚未设置明确目标。"
        answer = (
            f"{goal_text}今日摄入 {today['intake_kcal']} kcal、运动 "
            f"{today['activity_kcal']} kcal。模型暂时不可用，建议先保持规律记录，"
            "根据饥饿、训练和恢复状态做一次小幅调整。"
        )
        chunks = runtime.artifacts.get("knowledge.retrieve") or []
        citations = [
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
            for chunk in chunks[:2]
        ]
        return ToolExecution(
            step.id,
            tool,
            "completed",
            "已切换到确定性规则建议",
            int((time.perf_counter() - started) * 1000),
            answer=answer,
            citations=citations,
            output_summary={"citation_count": len(citations), "deterministic": True},
        )
    raise ValueError("tool_not_registered")


def execute_registered_tool(runtime: ToolRuntime, step: AgentPlanStep) -> ToolExecution:
    started = time.perf_counter()
    try:
        specialist_name = specialist_for_tool(step.tool)
        if specialist_name == "orchestrator":
            raise ValueError("orchestrator_cannot_execute_business_tool")
        return SPECIALIST_REGISTRY[specialist_name].execute(runtime, step, _execute)
    except (ValueError, RuntimeError) as error:
        return ToolExecution(
            step.id,
            step.tool,
            "failed",
            "工具执行失败，已停止依赖步骤并保留可安全完成的结果",
            int((time.perf_counter() - started) * 1000),
            error_code=str(error)[:80] or "tool_execution_failed",
            specialist=specialist_for_tool(step.tool),
        )
