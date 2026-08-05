from collections.abc import Callable
from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.model_router import ModelInvocation
from app.agent.policy import MAX_AGENT_REPLANS, validate_plan
from app.agent.tool_registry import TOOL_REGISTRY, ToolExecution
from app.schemas.agent import (
    AgentObservation,
    AgentPlan,
    AgentPlanStep,
    AgentRecoveryDecision,
    AgentVerification,
)

MAX_AGENT_V2_REPLANS = 1


class ExecutionState(TypedDict, total=False):
    cursor: int
    results: list[ToolExecution]
    replan_count: int
    skipped_step_ids: list[str]


@dataclass(frozen=True)
class ExecutionOutcome:
    executions: list[ToolExecution]
    observations: list[AgentObservation]
    verification: AgentVerification
    next_cursor: int
    waiting_for_user: bool


def run_execution_graph(
    plan: AgentPlan,
    execute: Callable[[AgentPlanStep], ToolExecution],
    *,
    initial_replan_count: int = 0,
) -> tuple[list[ToolExecution], AgentVerification]:
    if plan.needs_clarification:
        return [], AgentVerification(
            passed=False,
            completed_steps=0,
            failed_steps=0,
            skipped_steps=0,
            replan_count=min(initial_replan_count, MAX_AGENT_V2_REPLANS),
            reason=plan.clarification_question or "需要用户补充信息",
        )

    graph = StateGraph(ExecutionState)

    def executor(state: ExecutionState) -> ExecutionState:
        cursor = state.get("cursor", 0)
        results = list(state.get("results", []))
        skipped = set(state.get("skipped_step_ids", []))
        if cursor >= len(plan.steps):
            return state
        step = plan.steps[cursor]
        status_by_id = {item.step_id: item.status for item in results}
        blocked = any(
            status_by_id.get(dependency) in {"failed", "skipped"} for dependency in step.depends_on
        )
        if step.id in skipped or blocked:
            result = ToolExecution(
                step.id,
                step.tool,
                "skipped",
                "依赖步骤未完成，本步骤未执行",
                0,
                error_code="dependency_skipped",
            )
        else:
            result = execute(step)
        results.append(result)
        return {**state, "cursor": cursor + 1, "results": results}

    def verifier(state: ExecutionState) -> ExecutionState:
        return state

    def route(state: ExecutionState) -> str:
        results = state.get("results", [])
        replans = state.get("replan_count", 0)
        if results and results[-1].status == "failed" and replans < MAX_AGENT_V2_REPLANS:
            return "replan"
        if state.get("cursor", 0) < len(plan.steps):
            return "execute"
        return "end"

    def replan(state: ExecutionState) -> ExecutionState:
        results = state.get("results", [])
        failed_ids = {item.step_id for item in results if item.status == "failed"}
        skipped = set(state.get("skipped_step_ids", []))
        changed = True
        while changed:
            changed = False
            for step in plan.steps[state.get("cursor", 0) :]:
                if step.id not in skipped and any(
                    dependency in failed_ids or dependency in skipped
                    for dependency in step.depends_on
                ):
                    skipped.add(step.id)
                    changed = True
        return {
            **state,
            "replan_count": min(state.get("replan_count", 0) + 1, MAX_AGENT_V2_REPLANS),
            "skipped_step_ids": sorted(skipped),
        }

    graph.add_node("executor", executor)
    graph.add_node("verifier", verifier)
    graph.add_node("replan", replan)
    graph.add_edge(START, "executor")
    graph.add_edge("executor", "verifier")
    graph.add_conditional_edges(
        "verifier",
        route,
        {"execute": "executor", "replan": "replan", "end": END},
    )
    graph.add_edge("replan", "verifier")
    result = graph.compile().invoke(
        {
            "cursor": 0,
            "results": [],
            "replan_count": min(initial_replan_count, MAX_AGENT_V2_REPLANS),
            "skipped_step_ids": [],
        }
    )
    executions = result.get("results", [])
    completed = sum(item.status in {"completed", "awaiting_confirmation"} for item in executions)
    failed = sum(item.status == "failed" for item in executions)
    skipped = sum(item.status == "skipped" for item in executions)
    passed = failed == 0 and skipped == 0
    reason = (
        "所有计划步骤已完成或进入用户确认"
        if passed
        else "部分工具失败；依赖步骤已停止，独立步骤继续完成"
    )
    return executions, AgentVerification(
        passed=passed,
        completed_steps=completed,
        failed_steps=failed,
        skipped_steps=skipped,
        replan_count=result.get("replan_count", 0),
        reason=reason,
    )


def run_execution_graph_v3(
    plan: AgentPlan,
    execute: Callable[[AgentPlanStep], ToolExecution],
    replan: Callable[[AgentObservation], tuple[AgentRecoveryDecision, ModelInvocation]],
    *,
    start_cursor: int = 0,
    satisfied_step_ids: set[str] | None = None,
    initial_replan_count: int = 0,
) -> ExecutionOutcome:
    """Execute a bounded observe/verify/replan loop and pause at write checkpoints."""
    if plan.needs_clarification:
        verification = AgentVerification(
            passed=False,
            completed_steps=0,
            failed_steps=0,
            skipped_steps=0,
            replan_count=min(initial_replan_count, MAX_AGENT_REPLANS),
            reason=plan.clarification_question or "需要用户补充信息",
            decision="clarify",
        )
        return ExecutionOutcome([], [], verification, start_cursor, False)

    executions: list[ToolExecution] = []
    observations: list[AgentObservation] = []
    completed_ids = set(satisfied_step_ids or set())
    failed_ids: set[str] = set()
    recovered_ids: set[str] = set()
    replan_count = min(initial_replan_count, MAX_AGENT_REPLANS)
    cursor = start_cursor
    waiting = False

    def observe(execution: ToolExecution) -> AgentObservation:
        alternatives = list(TOOL_REGISTRY[execution.tool].recovery_tools)
        return AgentObservation(
            step_id=execution.step_id,
            tool=execution.tool,
            status=execution.status,
            error_type=execution.error_code,
            recoverable=execution.status == "failed" and bool(alternatives),
            output_summary=execution.output_summary,
            allowed_alternatives=alternatives,
        )

    while cursor < len(plan.steps):
        step = plan.steps[cursor]
        if any(dependency not in completed_ids for dependency in step.depends_on):
            execution = ToolExecution(
                step.id,
                step.tool,
                "skipped",
                "依赖步骤未完成，本步骤未执行",
                0,
                error_code="dependency_skipped",
            )
        else:
            execution = execute(step)
        executions.append(execution)
        observation = observe(execution)
        observations.append(observation)
        cursor += 1

        if execution.status in {"completed", "awaiting_confirmation"}:
            completed_ids.add(step.id)
        elif execution.status == "failed":
            failed_ids.add(step.id)
            if observation.recoverable and replan_count < MAX_AGENT_REPLANS:
                decision, invocation = replan(observation)
                replan_count += 1
                if (
                    decision.action == "use_alternative"
                    and decision.tool in observation.allowed_alternatives
                ):
                    recovery_step = AgentPlanStep(
                        id=f"recovery-{replan_count}",
                        tool=decision.tool,
                        reason=decision.reason,
                        segment=step.segment,
                    )
                    recovery_plan = AgentPlan(
                        goal="执行策略白名单内的故障恢复工具",
                        steps=[recovery_step],
                    )
                    if validate_plan(recovery_plan).allowed:
                        recovery = execute(recovery_step)
                        recovery.invocations.insert(0, invocation)
                        executions.append(recovery)
                        observations.append(observe(recovery))
                        if recovery.status == "completed":
                            recovered_ids.add(step.id)
                            completed_ids.add(step.id)

        if execution.status == "awaiting_confirmation":
            next_step = plan.steps[cursor] if cursor < len(plan.steps) else None
            if next_step is None or not next_step.requires_confirmation:
                waiting = True
                break

    failed = sum(item.status == "failed" for item in executions)
    skipped = sum(item.status == "skipped" for item in executions)
    completed = sum(item.status in {"completed", "awaiting_confirmation"} for item in executions)
    unrecovered = failed_ids - recovered_ids
    passed = not unrecovered and skipped == 0
    if waiting:
        decision_name = "wait_for_user"
        reason = "写入候选已生成；必须由用户确认后才能继续后续工具"
    elif recovered_ids:
        decision_name = "fallback"
        reason = "原工具失败后已通过白名单降级工具完成可解释恢复"
    elif passed:
        decision_name = "done"
        reason = "目标已完成，验证器未发现未恢复失败"
    else:
        decision_name = "stop"
        reason = "没有更多安全恢复路径，执行已停止"
    verification = AgentVerification(
        passed=passed,
        completed_steps=min(completed, 6),
        failed_steps=min(failed, 6),
        skipped_steps=min(skipped, 6),
        replan_count=replan_count,
        reason=reason,
        decision=decision_name,
        waiting_for_user=waiting,
        pending_confirmations=sum(item.status == "awaiting_confirmation" for item in executions),
    )
    return ExecutionOutcome(executions, observations, verification, cursor, waiting)
