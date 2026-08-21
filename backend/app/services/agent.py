import hashlib
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.execution_graph import run_execution_graph, run_execution_graph_v3
from app.agent.intent_router import route_intents
from app.agent.memory import memory_context, remember_confirmation, remember_run, resolve_thread
from app.agent.model_router import (
    KNOWLEDGE_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    ModelInvocation,
    ModelRouter,
)
from app.agent.planner import create_plan, deterministic_plan, redacted_plan
from app.agent.policy import validate_plan
from app.agent.replanner import choose_recovery
from app.agent.specialists import selected_specialists, specialist_for_tool
from app.agent.tool_registry import ToolRuntime, execute_registered_tool
from app.agent.tools import (
    add_tool_trace,
    build_write_candidate,
    read_journey_tool,
    read_profile_tool,
)
from app.agent.workflows import run_knowledge, run_recommendation, run_weekly_summary
from app.api.errors import APIError
from app.core.security import decode_agent_confirmation_token
from app.domain.enums import RecordSource
from app.models.agent import AgentConfirmation, AgentRun
from app.models.user import User
from app.schemas.agent import (
    AgentCandidate,
    AgentCitation,
    AgentConfirmationProgress,
    AgentConfirmationRequest,
    AgentConfirmationResponse,
    AgentEvent,
    AgentObservation,
    AgentPlan,
    AgentPlanStepResult,
    AgentRunResponse,
    AgentRunTrace,
    AgentToolTrace,
    AgentUsage,
    IntentItem,
)
from app.schemas.records import (
    ActivityRecordCreate,
    ActivityRecordResponse,
    FoodRecordCreate,
    FoodRecordResponse,
    WeightRecordCreate,
    WeightRecordResponse,
)
from app.services import records as record_service
from app.services.common import (
    commit_idempotent_or_replay,
    find_idempotent_response,
    store_idempotent_response,
)

SAFETY_NOTICE = "Journey 提供一般健身、营养和生活方式信息，不提供医疗诊断、治疗或处方建议。"
CHECKPOINT_TTL_MINUTES = 15


def _event(sequence: int, event_type: str, message: str, **data) -> AgentEvent:
    return AgentEvent(sequence=sequence, type=event_type, message=message, data=data)


def _sum_usage(invocations: list[ModelInvocation]) -> AgentUsage:
    if not invocations:
        return AgentUsage(provider="local", model="deterministic")
    return AgentUsage(
        provider=invocations[-1].provider,
        model=invocations[-1].model,
        input_tokens=sum(item.input_tokens for item in invocations),
        output_tokens=sum(item.output_tokens for item in invocations),
        retries=sum(item.retries for item in invocations),
        latency_ms=sum(item.latency_ms for item in invocations),
        estimated_cost_usd=round(sum(item.estimated_cost_usd for item in invocations), 8),
    )


def _candidate_summary(candidate: AgentCandidate) -> dict:
    if candidate.kind == "food":
        return {
            "kind": "food",
            "energy_present": candidate.payload.energy_kcal is not None,
        }
    if candidate.kind == "activity":
        return {
            "kind": "activity",
            "duration_present": candidate.payload.duration_minutes is not None,
        }
    return {"kind": "weight", "value_present": True}


def _confirmation_progress(db: Session, run: AgentRun) -> AgentConfirmationProgress:
    confirmations = list(
        db.scalars(select(AgentConfirmation).where(AgentConfirmation.run_id == run.id))
    )
    confirmed = sum(item.used_at is not None for item in confirmations)
    pending = len(confirmations) - confirmed
    return AgentConfirmationProgress(
        total=len(confirmations),
        confirmed=confirmed,
        pending=pending,
        resume_available=run.status == "waiting_for_user" and bool(confirmations) and pending == 0,
    )


def _public_intents(intent_names: list[str]) -> list[IntentItem]:
    return [IntentItem(intent=name, confidence=1, segment="") for name in intent_names]


def _agents_for_intents(intent_names: list[str]) -> list[str]:
    tools: list[str] = []
    for intent in intent_names:
        if intent in {"food", "activity", "weight"}:
            tools.append(f"{intent}.parse_candidate")
        elif intent == "knowledge":
            tools.append("knowledge.answer")
        elif intent in {"recommendation", "weekly_summary"}:
            tools.extend(["context.load", "knowledge.retrieve", f"{intent}.generate"])
        elif intent == "profile":
            tools.append("profile.read")
        elif intent == "history":
            tools.append("journey.read")
    return selected_specialists(tools)


def _add_orchestrator_traces(
    db: Session,
    run: AgentRun,
    *,
    intents: list[str],
    plan: AgentPlan,
    route_invocation: ModelInvocation,
    planner_invocation: ModelInvocation,
) -> None:
    agents = selected_specialists([step.tool for step in plan.steps])
    add_tool_trace(
        db,
        run_id=run.id,
        tool_name="orchestrator.router",
        started=time.perf_counter(),
        input_summary={"input_length": run.input_length},
        output_summary={"intents": intents, "selected_agents": agents},
        error_code=route_invocation.error_code,
        latency_ms=route_invocation.latency_ms,
    )
    add_tool_trace(
        db,
        run_id=run.id,
        tool_name="orchestrator.planner",
        started=time.perf_counter(),
        input_summary={"intent_count": len(intents)},
        output_summary={"step_count": len(plan.steps), "selected_agents": agents},
        error_code=planner_invocation.error_code,
        latency_ms=planner_invocation.latency_ms,
    )


def _run_agent_v1(
    db: Session,
    user: User,
    *,
    message: str,
    request_id: str,
    model_router: ModelRouter | None = None,
) -> AgentRunResponse:
    started = time.perf_counter()
    router = model_router or ModelRouter(db)
    run = AgentRun(
        user_id=user.id,
        request_id=request_id,
        status="running",
        input_hash=hashlib.sha256(message.encode("utf-8")).hexdigest(),
        input_length=len(message),
        intents=[],
        provider=router.adapter.provider,
        model=router.model_for("intent_classification"),
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        knowledge_version=KNOWLEDGE_VERSION,
    )
    db.add(run)
    db.flush()

    events: list[AgentEvent] = [_event(0, "status", "正在理解你的输入")]
    candidates: list[AgentCandidate] = []
    citations: list[AgentCitation] = []
    answers: list[str] = []
    invocations: list[ModelInvocation] = []
    plan, route_invocation = route_intents(router, message)
    invocations.append(route_invocation)
    run.intents = [item.intent for item in plan.intents]
    sequence = 1

    for item in plan.intents:
        tool_started = time.perf_counter()
        if item.intent in {"food", "activity", "weight"}:
            try:
                candidate, invocation = build_write_candidate(
                    db, user, run.id, item.intent, item.segment, router
                )
                invocations.append(invocation)
                candidates.append(candidate)
                summary = _candidate_summary(candidate)
                add_tool_trace(
                    db,
                    run_id=run.id,
                    tool_name=f"{item.intent}.parse_candidate",
                    started=tool_started,
                    input_summary={"text_length": len(item.segment)},
                    output_summary=summary,
                )
                events.append(
                    _event(
                        sequence,
                        "candidate",
                        "已生成候选，请核对后确认保存",
                        candidate_id=str(candidate.candidate_id),
                        kind=candidate.kind,
                    )
                )
            except (ValueError, RuntimeError):
                add_tool_trace(
                    db,
                    run_id=run.id,
                    tool_name=f"{item.intent}.parse_candidate",
                    started=tool_started,
                    status="failed",
                    input_summary={"text_length": len(item.segment)},
                    error_code="candidate_parse_failed",
                )
                events.append(
                    _event(
                        sequence,
                        "error",
                        "没有提取出可靠记录，请补充具体内容和数值",
                        intent=item.intent,
                    )
                )
            sequence += 1
            continue

        if item.intent == "profile":
            profile = read_profile_tool(db, user)
            add_tool_trace(
                db,
                run_id=run.id,
                tool_name="profile.read",
                started=tool_started,
                output_summary={"profile_available": True},
            )
            answers.append(
                f"你的当前画像昵称是 {profile['display_name']}，"
                f"最新体重为 {profile.get('latest_weight_kg') or '未记录'} kg。"
            )
            events.append(_event(sequence, "tool", "已读取当前用户画像", tool="profile.read"))
        elif item.intent == "history":
            history = read_journey_tool(db, user)
            add_tool_trace(
                db,
                run_id=run.id,
                tool_name="journey.read",
                started=tool_started,
                output_summary={"days_returned": len(history["items"])},
            )
            answers.append(
                f"最近返回 {len(history['items'])} 个有记录的日期，可在 Journey 查看明细。"
            )
            events.append(_event(sequence, "tool", "已读取近期 Journey", tool="journey.read"))
        elif item.intent in {"knowledge", "recommendation", "weekly_summary"}:
            result = (
                run_knowledge(db, router, item.segment)
                if item.intent == "knowledge"
                else run_recommendation(db, user, router)
                if item.intent == "recommendation"
                else run_weekly_summary(db, user, router)
            )
            invocations.append(result.invocation)
            answers.append(result.answer)
            citations.extend(result.citations)
            for node in result.node_traces:
                add_tool_trace(
                    db,
                    run_id=run.id,
                    tool_name=node["name"],
                    started=time.perf_counter(),
                    output_summary=node.get("output_summary"),
                    error_code=node.get("error_code"),
                    latency_ms=node["latency_ms"],
                )
            add_tool_trace(
                db,
                run_id=run.id,
                tool_name=f"{item.intent}.workflow",
                started=tool_started,
                output_summary={"citation_count": len(result.citations)},
                error_code=result.invocation.error_code,
            )
            events.append(
                _event(
                    sequence,
                    "knowledge",
                    "已完成受控知识检索与生成",
                    citation_count=len(result.citations),
                )
            )
        else:
            events.append(
                _event(
                    sequence,
                    "status",
                    plan.clarification_question or "请补充你要记录或查询的具体内容。",
                )
            )
        sequence += 1

    usage = _sum_usage(invocations)
    fallback_used = any(item.fallback_used for item in invocations)
    status = (
        "clarification_required"
        if plan.needs_clarification or all(item.intent == "clarify" for item in plan.intents)
        else "degraded"
        if any(item.type == "error" for item in events)
        or any(item.error_code for item in invocations)
        else "completed"
    )
    events.append(_event(sequence, "complete", "本次处理已完成", status=status))
    run.status = status
    run.provider = usage.provider
    run.model = usage.model
    run.input_tokens = usage.input_tokens
    run.output_tokens = usage.output_tokens
    run.retries = usage.retries
    run.estimated_cost_usd = Decimal(str(usage.estimated_cost_usd))
    run.fallback_used = fallback_used
    run.error_code = next((item.error_code for item in invocations if item.error_code), None)
    run.latency_ms = int((time.perf_counter() - started) * 1000)
    run.completed_at = datetime.now(UTC)
    db.commit()

    return AgentRunResponse(
        run_id=run.id,
        status=status,
        intents=plan.intents,
        events=events,
        candidates=candidates,
        answer="\n\n".join(answers) or plan.clarification_question,
        citations=citations,
        fallback_used=fallback_used,
        safety_notice=SAFETY_NOTICE,
        usage=usage.model_copy(update={"latency_ms": run.latency_ms}),
        selected_agents=_agents_for_intents(run.intents),
    )


def _run_agent_v2(
    db: Session,
    user: User,
    *,
    message: str,
    request_id: str,
    thread_id: uuid.UUID | None,
    model_router: ModelRouter,
) -> AgentRunResponse:
    started = time.perf_counter()
    thread = resolve_thread(db, user, thread_id)
    recent_memory = memory_context(thread)
    run = AgentRun(
        user_id=user.id,
        thread_id=thread.id,
        request_id=request_id,
        status="running",
        input_hash=hashlib.sha256(message.encode("utf-8")).hexdigest(),
        input_length=len(message),
        intents=[],
        plan={},
        verification={},
        replan_count=0,
        provider=model_router.adapter.provider,
        model=model_router.model_for("intent_classification"),
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        knowledge_version=KNOWLEDGE_VERSION,
    )
    db.add(run)
    db.flush()

    events: list[AgentEvent] = [_event(0, "status", "正在理解目标并制定执行计划")]
    intent_plan, route_invocation = route_intents(model_router, message, recent_memory)
    plan, planner_invocation = create_plan(
        model_router,
        message=message,
        intent_plan=intent_plan,
        memory_context=recent_memory,
    )
    invocations = [route_invocation, planner_invocation]
    run.intents = [item.intent for item in intent_plan.intents]
    _add_orchestrator_traces(
        db,
        run,
        intents=run.intents,
        plan=plan,
        route_invocation=route_invocation,
        planner_invocation=planner_invocation,
    )

    policy_started = time.perf_counter()
    decision = validate_plan(plan)
    policy_replan_count = 0
    if not decision.allowed:
        plan = deterministic_plan(message, intent_plan)
        fallback_decision = validate_plan(plan)
        if not fallback_decision.allowed:
            raise RuntimeError("deterministic_agent_plan_rejected")
        policy_replan_count = 1
    public_plan = redacted_plan(plan)
    run.plan = public_plan.model_dump(mode="json")
    add_tool_trace(
        db,
        run_id=run.id,
        tool_name="policy.guard",
        started=policy_started,
        status="completed" if decision.allowed else "replanned",
        input_summary={"step_count": len(plan.steps)},
        output_summary={
            "allowed": True,
            "original_plan_allowed": decision.allowed,
            "violation_codes": list(decision.violations),
        },
    )
    events.append(
        _event(
            1,
            "status",
            "执行计划已通过策略校验"
            if decision.allowed
            else "模型计划未通过策略校验，已切换为确定性安全计划",
            step_count=len(plan.steps),
            replan_count=policy_replan_count,
        )
    )

    runtime = ToolRuntime(db=db, user=user, run_id=run.id, model_router=model_router)
    executions, verification = run_execution_graph(
        plan,
        lambda step: execute_registered_tool(runtime, step),
        initial_replan_count=policy_replan_count,
    )
    candidates: list[AgentCandidate] = []
    citations: list[AgentCitation] = []
    answers: list[str] = []
    sequence = 2
    step_results: list[AgentPlanStepResult] = []
    for execution in executions:
        invocations.extend(execution.invocations)
        candidates.extend(execution.candidates)
        citations.extend(execution.citations)
        if execution.answer:
            answers.append(execution.answer)
        add_tool_trace(
            db,
            run_id=run.id,
            tool_name=execution.tool,
            started=time.perf_counter(),
            status=execution.status,
            input_summary={"step_id": execution.step_id},
            output_summary=execution.output_summary,
            error_code=execution.error_code,
            latency_ms=execution.latency_ms,
        )
        for node in execution.node_traces:
            add_tool_trace(
                db,
                run_id=run.id,
                tool_name=node["name"],
                started=time.perf_counter(),
                status="failed" if node.get("error_code") else "completed",
                output_summary=node.get("output_summary"),
                error_code=node.get("error_code"),
                latency_ms=node["latency_ms"],
            )
        step_results.append(
            AgentPlanStepResult(
                step_id=execution.step_id,
                tool=execution.tool,
                status=execution.status,
                message=execution.message,
                error_code=execution.error_code,
                specialist=execution.specialist,
                duration_ms=execution.latency_ms,
            )
        )
        event_type = (
            "candidate"
            if execution.status == "awaiting_confirmation"
            else "error"
            if execution.status == "failed"
            else "status"
            if execution.status == "skipped"
            else "tool"
        )
        events.append(
            _event(
                sequence,
                event_type,
                execution.message,
                step_id=execution.step_id,
                tool=execution.tool,
                status=execution.status,
                specialist=execution.specialist,
            )
        )
        sequence += 1

    if verification.replan_count > policy_replan_count:
        events.append(
            _event(
                sequence,
                "status",
                "执行失败后已进行一次受控重规划，依赖步骤已停止",
                replan_count=verification.replan_count,
            )
        )
        sequence += 1

    usage = _sum_usage(invocations)
    fallback_used = any(item.fallback_used for item in invocations)
    status = (
        "clarification_required"
        if plan.needs_clarification or all(item.intent == "clarify" for item in intent_plan.intents)
        else "degraded"
        if not verification.passed or any(item.error_code for item in invocations)
        else "completed"
    )
    events.append(_event(sequence, "complete", "本次 Agent 计划执行已结束", status=status))
    run.status = status
    run.provider = usage.provider
    run.model = usage.model
    run.input_tokens = usage.input_tokens
    run.output_tokens = usage.output_tokens
    run.retries = usage.retries
    run.estimated_cost_usd = Decimal(str(usage.estimated_cost_usd))
    run.fallback_used = fallback_used
    run.error_code = next(
        (item.error_code for item in [*invocations, *executions] if item.error_code),
        None,
    )
    run.replan_count = verification.replan_count
    run.verification = verification.model_dump(mode="json")
    run.latency_ms = int((time.perf_counter() - started) * 1000)
    run.completed_at = datetime.now(UTC)
    remember_run(thread, run, candidates=candidates, answer_present=bool(answers))
    db.commit()

    return AgentRunResponse(
        run_id=run.id,
        thread_id=thread.id,
        status=status,
        intents=intent_plan.intents,
        plan=public_plan,
        step_results=step_results,
        verification=verification,
        events=events,
        candidates=candidates,
        answer="\n\n".join(answers) or plan.clarification_question,
        citations=citations,
        fallback_used=fallback_used,
        safety_notice=SAFETY_NOTICE,
        usage=usage.model_copy(update={"latency_ms": run.latency_ms}),
        selected_agents=selected_specialists([step.tool for step in plan.steps]),
    )


def _collect_v3_executions(
    db: Session,
    run: AgentRun,
    executions,
    *,
    events: list[AgentEvent],
    start_sequence: int,
) -> tuple[
    list[AgentPlanStepResult],
    list[AgentCandidate],
    list[AgentCitation],
    list[str],
    list[ModelInvocation],
]:
    step_results: list[AgentPlanStepResult] = []
    candidates: list[AgentCandidate] = []
    citations: list[AgentCitation] = []
    answers: list[str] = []
    invocations: list[ModelInvocation] = []
    sequence = start_sequence
    for execution in executions:
        if execution.step_id.startswith("recovery-"):
            add_tool_trace(
                db,
                run_id=run.id,
                tool_name="policy.recovery_guard",
                started=time.perf_counter(),
                status="completed",
                input_summary={"step_id": execution.step_id},
                output_summary={"allowed": True, "tool": execution.tool},
                latency_ms=0,
            )
        invocations.extend(execution.invocations)
        candidates.extend(execution.candidates)
        citations.extend(execution.citations)
        if execution.answer:
            answers.append(execution.answer)
        add_tool_trace(
            db,
            run_id=run.id,
            tool_name=execution.tool,
            started=time.perf_counter(),
            status=execution.status,
            input_summary={"step_id": execution.step_id},
            output_summary=execution.output_summary,
            error_code=execution.error_code,
            latency_ms=execution.latency_ms,
        )
        for node in execution.node_traces:
            add_tool_trace(
                db,
                run_id=run.id,
                tool_name=node["name"],
                started=time.perf_counter(),
                status="failed" if node.get("error_code") else "completed",
                output_summary=node.get("output_summary"),
                error_code=node.get("error_code"),
                latency_ms=node["latency_ms"],
            )
        step_results.append(
            AgentPlanStepResult(
                step_id=execution.step_id,
                tool=execution.tool,
                status=execution.status,
                message=execution.message,
                error_code=execution.error_code,
                specialist=execution.specialist,
                duration_ms=execution.latency_ms,
            )
        )
        event_type = (
            "candidate"
            if execution.status == "awaiting_confirmation"
            else "error"
            if execution.status == "failed"
            else "status"
            if execution.status == "skipped"
            else "tool"
        )
        events.append(
            _event(
                sequence,
                event_type,
                execution.message,
                step_id=execution.step_id,
                tool=execution.tool,
                status=execution.status,
                specialist=execution.specialist,
            )
        )
        sequence += 1
    return step_results, candidates, citations, answers, invocations


def _run_agent_v3(
    db: Session,
    user: User,
    *,
    message: str,
    request_id: str,
    thread_id: uuid.UUID | None,
    model_router: ModelRouter,
) -> AgentRunResponse:
    started = time.perf_counter()
    thread = resolve_thread(db, user, thread_id)
    recent_memory = memory_context(thread)
    run = AgentRun(
        user_id=user.id,
        thread_id=thread.id,
        request_id=request_id,
        status="running",
        input_hash=hashlib.sha256(message.encode("utf-8")).hexdigest(),
        input_length=len(message),
        intents=[],
        plan={},
        verification={},
        observations=[],
        checkpoint={},
        replan_count=0,
        resume_count=0,
        provider=model_router.adapter.provider,
        model=model_router.model_for("intent_classification"),
        prompt_version=PROMPT_VERSION,
        schema_version="journey-agent-schema-3.0.0",
        knowledge_version=KNOWLEDGE_VERSION,
    )
    db.add(run)
    db.flush()

    events = [_event(0, "status", "正在理解目标并制定可暂停执行计划")]
    intent_plan, route_invocation = route_intents(model_router, message, recent_memory)
    plan, planner_invocation = create_plan(
        model_router,
        message=message,
        intent_plan=intent_plan,
        memory_context=recent_memory,
    )
    invocations = [route_invocation, planner_invocation]
    run.intents = [item.intent for item in intent_plan.intents]
    _add_orchestrator_traces(
        db,
        run,
        intents=run.intents,
        plan=plan,
        route_invocation=route_invocation,
        planner_invocation=planner_invocation,
    )

    policy_started = time.perf_counter()
    decision = validate_plan(plan)
    policy_replan_count = 0
    if not decision.allowed:
        plan = deterministic_plan(message, intent_plan)
        fallback_decision = validate_plan(plan)
        if not fallback_decision.allowed:
            raise RuntimeError("deterministic_agent_plan_rejected")
        policy_replan_count = 1
    public_plan = redacted_plan(plan)
    run.plan = public_plan.model_dump(mode="json")
    add_tool_trace(
        db,
        run_id=run.id,
        tool_name="policy.guard",
        started=policy_started,
        status="completed" if decision.allowed else "replanned",
        input_summary={"step_count": len(plan.steps)},
        output_summary={
            "allowed": True,
            "original_plan_allowed": decision.allowed,
            "violation_codes": list(decision.violations),
        },
    )
    events.append(
        _event(
            1,
            "verification",
            "执行计划已通过策略校验"
            if decision.allowed
            else "模型计划未通过策略校验，已切换为确定性安全计划",
            step_count=len(plan.steps),
            replan_count=policy_replan_count,
        )
    )

    runtime = ToolRuntime(db=db, user=user, run_id=run.id, model_router=model_router)
    outcome = run_execution_graph_v3(
        plan,
        lambda step: execute_registered_tool(runtime, step),
        lambda observation: choose_recovery(model_router, observation),
        initial_replan_count=policy_replan_count,
    )
    step_results, candidates, citations, answers, execution_invocations = _collect_v3_executions(
        db, run, outcome.executions, events=events, start_sequence=2
    )
    invocations.extend(execution_invocations)
    for index, observation in enumerate(outcome.observations, start=len(events)):
        events.append(
            _event(
                index,
                "observation",
                "已记录工具结果并交由验证器决策",
                step_id=observation.step_id,
                status=observation.status,
                recoverable=observation.recoverable,
            )
        )

    usage = _sum_usage(invocations)
    fallback_used = any(item.fallback_used for item in invocations) or any(
        item.step_id.startswith("recovery-") for item in outcome.executions
    )
    recovery_used = any(item.step_id.startswith("recovery-") for item in outcome.executions)
    if outcome.waiting_for_user:
        status = "waiting_for_user"
        run.checkpoint = {
            "version": "1",
            "next_cursor": outcome.next_cursor,
            "satisfied_step_ids": [
                item.step_id
                for item in outcome.executions
                if item.status == "awaiting_confirmation"
            ],
            "status": "waiting",
        }
        run.checkpoint_expires_at = datetime.now(UTC) + timedelta(minutes=CHECKPOINT_TTL_MINUTES)
        run.completed_at = None
        events.append(
            _event(
                len(events),
                "verification",
                "验证器已暂停：请确认全部候选后显式继续",
                decision="wait_for_user",
            )
        )
    else:
        status = (
            "clarification_required"
            if outcome.verification.decision == "clarify"
            else "degraded"
            if not outcome.verification.passed or recovery_used
            else "completed"
        )
        run.checkpoint = {"version": "1", "status": "consumed"}
        run.completed_at = datetime.now(UTC)
        remember_run(thread, run, candidates=candidates, answer_present=bool(answers))
        events.append(_event(len(events), "complete", "本次 Agent 计划执行已结束", status=status))

    run.status = status
    if status == "waiting_for_user":
        remember_run(thread, run, candidates=candidates, answer_present=False)
    run.provider = usage.provider
    run.model = usage.model
    run.input_tokens = usage.input_tokens
    run.output_tokens = usage.output_tokens
    run.retries = usage.retries
    run.estimated_cost_usd = Decimal(str(usage.estimated_cost_usd))
    run.fallback_used = fallback_used
    run.error_code = next(
        (item.error_code for item in [*invocations, *outcome.executions] if item.error_code),
        None,
    )
    run.replan_count = outcome.verification.replan_count
    run.verification = outcome.verification.model_dump(mode="json")
    run.observations = [item.model_dump(mode="json") for item in outcome.observations]
    run.latency_ms = int((time.perf_counter() - started) * 1000)
    db.commit()
    progress = _confirmation_progress(db, run) if candidates else None
    return AgentRunResponse(
        run_id=run.id,
        thread_id=thread.id,
        status=status,
        intents=intent_plan.intents,
        plan=public_plan,
        step_results=step_results,
        verification=outcome.verification,
        observations=outcome.observations,
        confirmation_progress=progress,
        resumable=bool(progress and progress.resume_available),
        events=events,
        candidates=candidates,
        answer="\n\n".join(answers) or plan.clarification_question,
        citations=citations,
        fallback_used=fallback_used,
        safety_notice=SAFETY_NOTICE,
        usage=usage.model_copy(update={"latency_ms": run.latency_ms}),
        selected_agents=selected_specialists([step.tool for step in plan.steps]),
    )


def resume_agent_run(
    db: Session,
    user: User,
    *,
    run_id: uuid.UUID,
    model_router: ModelRouter | None = None,
) -> AgentRunResponse:
    started = time.perf_counter()
    run = db.scalar(
        select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user.id).with_for_update()
    )
    if run is None:
        raise APIError(status_code=404, code="agent_run_not_found", message="Agent run not found")
    if run.status != "waiting_for_user" or run.checkpoint.get("status") != "waiting":
        raise APIError(
            status_code=409, code="agent_run_not_resumable", message="Run is not waiting"
        )
    if run.checkpoint_expires_at is None or run.checkpoint_expires_at <= datetime.now(UTC):
        run.checkpoint = {**run.checkpoint, "status": "expired"}
        db.commit()
        raise APIError(
            status_code=409, code="agent_checkpoint_expired", message="Checkpoint expired"
        )
    progress = _confirmation_progress(db, run)
    if progress.pending:
        raise APIError(
            status_code=409,
            code="agent_confirmations_pending",
            message="Confirm all candidates before resuming",
        )

    router = model_router or ModelRouter(db)
    plan = AgentPlan.model_validate(run.plan)
    cursor = int(run.checkpoint.get("next_cursor", 0))
    satisfied = set(run.checkpoint.get("satisfied_step_ids", []))
    runtime = ToolRuntime(db=db, user=user, run_id=run.id, model_router=router)
    outcome = run_execution_graph_v3(
        plan,
        lambda step: execute_registered_tool(runtime, step),
        lambda observation: choose_recovery(router, observation),
        start_cursor=cursor,
        satisfied_step_ids=satisfied,
        initial_replan_count=run.replan_count,
    )
    events = [_event(0, "status", "候选已确认，正在从安全检查点继续执行")]
    step_results, candidates, citations, answers, invocations = _collect_v3_executions(
        db, run, outcome.executions, events=events, start_sequence=1
    )
    prior_observations = [AgentObservation.model_validate(item) for item in run.observations]
    observations = [*prior_observations, *outcome.observations]
    usage = _sum_usage(invocations)
    fallback_used = (
        run.fallback_used
        or any(item.fallback_used for item in invocations)
        or any(item.step_id.startswith("recovery-") for item in outcome.executions)
    )
    had_execution_failure = any(item.status == "failed" for item in observations)
    status = (
        "waiting_for_user"
        if outcome.waiting_for_user
        else "degraded"
        if not outcome.verification.passed or had_execution_failure
        else "completed"
    )
    run.status = status
    run.resume_count += 1
    run.replan_count = outcome.verification.replan_count
    run.verification = outcome.verification.model_dump(mode="json")
    run.observations = [item.model_dump(mode="json") for item in observations]
    run.input_tokens += usage.input_tokens
    run.output_tokens += usage.output_tokens
    run.retries += usage.retries
    run.estimated_cost_usd = Decimal(str(float(run.estimated_cost_usd) + usage.estimated_cost_usd))
    run.fallback_used = fallback_used
    run.latency_ms += int((time.perf_counter() - started) * 1000)
    if outcome.waiting_for_user:
        run.checkpoint = {
            "version": "1",
            "next_cursor": outcome.next_cursor,
            "satisfied_step_ids": sorted(satisfied),
            "status": "waiting",
        }
    else:
        run.checkpoint = {"version": "1", "status": "consumed"}
        run.completed_at = datetime.now(UTC)
        if run.thread is not None:
            remember_run(run.thread, run, candidates=candidates, answer_present=bool(answers))
    events.append(
        _event(
            len(events),
            "verification",
            outcome.verification.reason,
            decision=outcome.verification.decision,
        )
    )
    events.append(_event(len(events), "complete", "检查点续跑已结束", status=status))
    db.commit()
    current_progress = _confirmation_progress(db, run)
    return AgentRunResponse(
        run_id=run.id,
        thread_id=run.thread_id,
        status=status,
        intents=_public_intents(run.intents),
        plan=plan,
        step_results=step_results,
        verification=outcome.verification,
        observations=observations,
        confirmation_progress=current_progress,
        resumable=bool(current_progress.resume_available),
        events=events,
        candidates=candidates,
        answer="\n\n".join(answers) or None,
        citations=citations,
        fallback_used=fallback_used,
        safety_notice=SAFETY_NOTICE,
        usage=AgentUsage(
            provider=run.provider,
            model=run.model,
            input_tokens=run.input_tokens,
            output_tokens=run.output_tokens,
            retries=run.retries,
            latency_ms=run.latency_ms,
            estimated_cost_usd=float(run.estimated_cost_usd),
        ),
        selected_agents=selected_specialists([step.tool for step in plan.steps]),
    )


def run_agent(
    db: Session,
    user: User,
    *,
    message: str,
    request_id: str,
    thread_id: uuid.UUID | None = None,
    model_router: ModelRouter | None = None,
) -> AgentRunResponse:
    router = model_router or ModelRouter(db)
    if not router.settings.agent_v2_enabled:
        return _run_agent_v1(
            db,
            user,
            message=message,
            request_id=request_id,
            model_router=router,
        )
    if not router.settings.agent_v3_enabled:
        return _run_agent_v2(
            db,
            user,
            message=message,
            request_id=request_id,
            thread_id=thread_id,
            model_router=router,
        )
    return _run_agent_v3(
        db,
        user,
        message=message,
        request_id=request_id,
        thread_id=thread_id,
        model_router=router,
    )


def get_run_trace(db: Session, user: User, run_id: uuid.UUID) -> AgentRunTrace:
    run = db.scalar(select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user.id))
    if run is None:
        raise APIError(status_code=404, code="agent_run_not_found", message="Agent run not found")
    tools = sorted(run.tool_runs, key=lambda item: item.created_at)
    checkpoint_status = run.checkpoint.get("status", "none") if run.checkpoint else "none"
    if (
        checkpoint_status == "waiting"
        and run.checkpoint_expires_at is not None
        and run.checkpoint_expires_at <= datetime.now(UTC)
    ):
        checkpoint_status = "expired"
    progress = _confirmation_progress(db, run)
    confirmation_progress = progress if progress.total else None
    return AgentRunTrace(
        run_id=run.id,
        thread_id=run.thread_id,
        status=run.status,
        intents=run.intents,
        plan=run.plan or None,
        verification=run.verification or None,
        observations=run.observations or [],
        replan_count=run.replan_count,
        resume_count=run.resume_count,
        checkpoint_status=checkpoint_status,
        provider=run.provider,
        model=run.model,
        prompt_version=run.prompt_version,
        schema_version=run.schema_version,
        knowledge_version=run.knowledge_version,
        input_tokens=run.input_tokens,
        output_tokens=run.output_tokens,
        latency_ms=run.latency_ms,
        retries=run.retries,
        estimated_cost_usd=float(run.estimated_cost_usd),
        fallback_used=run.fallback_used,
        error_code=run.error_code,
        created_at=run.created_at,
        completed_at=run.completed_at,
        tools=[
            AgentToolTrace.model_validate(tool).model_copy(
                update={"specialist": specialist_for_tool(tool.tool_name)}
            )
            for tool in tools
        ],
        selected_agents=selected_specialists(
            [step.get("tool", "") for step in (run.plan or {}).get("steps", [])]
        ),
        confirmation_progress=confirmation_progress,
    )


def confirm_candidate(
    db: Session,
    user: User,
    *,
    candidate_id: uuid.UUID,
    payload: AgentConfirmationRequest,
    request_id: str,
    path: str,
    idempotency_key: str,
) -> AgentConfirmationResponse | dict:
    request_body = payload.model_dump(mode="json")
    replay = find_idempotent_response(
        db,
        user_id=user.id,
        method="POST",
        path=path,
        key=idempotency_key,
        payload=request_body,
    )
    if replay is not None:
        return {**replay, "replayed": True}

    claims = decode_agent_confirmation_token(payload.confirmation_token)
    if (
        claims is None
        or claims.user_id != user.id
        or claims.candidate_id != candidate_id
        or claims.kind != payload.kind
    ):
        raise APIError(
            status_code=400,
            code="invalid_confirmation_token",
            message="Confirmation token is invalid or expired",
        )
    confirmation = db.scalar(
        select(AgentConfirmation)
        .where(
            AgentConfirmation.candidate_id == candidate_id,
            AgentConfirmation.user_id == user.id,
        )
        .with_for_update()
    )
    token_hash = hashlib.sha256(payload.confirmation_token.encode("utf-8")).hexdigest()
    if confirmation is None or not secrets.compare_digest(confirmation.token_hash, token_hash):
        raise APIError(
            status_code=400,
            code="invalid_confirmation_token",
            message="Confirmation token is invalid or expired",
        )
    if confirmation.run_id != claims.run_id or confirmation.kind != claims.kind:
        raise APIError(
            status_code=400,
            code="invalid_confirmation_token",
            message="Confirmation token is invalid or expired",
        )
    if confirmation.used_at is not None:
        raise APIError(
            status_code=409,
            code="confirmation_already_used",
            message="This candidate has already been confirmed",
        )
    if confirmation.expires_at <= datetime.now(UTC):
        raise APIError(
            status_code=400,
            code="confirmation_expired",
            message="Confirmation token has expired",
        )

    origin_run = db.get(AgentRun, confirmation.run_id)
    if payload.kind == "food" and isinstance(payload.payload, FoodRecordCreate):
        record_source = (
            RecordSource.IMAGE
            if origin_run is not None and "food_image" in origin_run.intents
            else RecordSource.AGENT
        )
        values = payload.payload.model_copy(
            update={"source": record_source, "source_ref": str(candidate_id)}
        )
        record = record_service.create_food(db, user, values, request_id)
        body = FoodRecordResponse.model_validate(record).model_dump(mode="json")
    elif payload.kind == "activity" and isinstance(payload.payload, ActivityRecordCreate):
        values = payload.payload.model_copy(
            update={"source": RecordSource.AGENT, "source_ref": str(candidate_id)}
        )
        record = record_service.create_activity(db, user, values, request_id)
        body = ActivityRecordResponse.model_validate(record).model_dump(mode="json")
    elif payload.kind == "weight" and isinstance(payload.payload, WeightRecordCreate):
        values = payload.payload.model_copy(update={"source": RecordSource.AGENT})
        record = record_service.create_weight(db, user, values, request_id)
        body = WeightRecordResponse.model_validate(record).model_dump(mode="json")
    else:
        raise APIError(
            status_code=422,
            code="candidate_payload_mismatch",
            message="Candidate kind does not match payload schema",
        )

    confirmation.used_at = datetime.now(UTC)
    confirmation.result_record_id = str(record.id)
    if origin_run is not None:
        remember_confirmation(db, origin_run, payload.kind)
    db.flush()
    progress = _confirmation_progress(db, origin_run) if origin_run is not None else None
    if (
        origin_run is not None
        and progress is not None
        and progress.pending == 0
        and origin_run.status == "waiting_for_user"
        and int(origin_run.checkpoint.get("next_cursor", 0))
        >= len(origin_run.plan.get("steps", []))
    ):
        origin_run.status = "completed"
        origin_run.checkpoint = {"version": "1", "status": "consumed"}
        origin_run.completed_at = datetime.now(UTC)
        origin_run.verification = {
            **origin_run.verification,
            "decision": "done",
            "waiting_for_user": False,
            "pending_confirmations": 0,
            "reason": "候选已全部确认，本次运行没有待续跑步骤",
        }
        if origin_run.thread is not None:
            remember_run(origin_run.thread, origin_run, candidates=[], answer_present=False)
        progress = _confirmation_progress(db, origin_run)
    response = AgentConfirmationResponse(
        candidate_id=candidate_id,
        kind=payload.kind,
        record=body,
        run_id=origin_run.id if origin_run is not None else None,
        run_status=origin_run.status if origin_run is not None else None,
        confirmation_progress=progress,
        resume_available=bool(progress and progress.resume_available),
    ).model_dump(mode="json")
    store_idempotent_response(
        db,
        user_id=user.id,
        method="POST",
        path=path,
        key=idempotency_key,
        payload=request_body,
        status_code=201,
        response_body=response,
    )
    return (
        commit_idempotent_or_replay(
            db,
            user_id=user.id,
            method="POST",
            path=path,
            key=idempotency_key,
            payload=request_body,
        )
        or response
    )
