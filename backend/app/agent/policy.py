from dataclasses import dataclass

from app.agent.tool_registry import TOOL_REGISTRY
from app.schemas.agent import AgentPlan

MAX_AGENT_STEPS = 6
MAX_AGENT_REPLANS = 2


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    violations: tuple[str, ...]


def validate_plan(plan: AgentPlan) -> PolicyDecision:
    violations: list[str] = []
    if len(plan.steps) > MAX_AGENT_STEPS:
        violations.append("step_limit_exceeded")
    seen: set[str] = set()
    tool_by_id: dict[str, str] = {}
    for step in plan.steps:
        spec = TOOL_REGISTRY.get(step.tool)
        if spec is None:
            violations.append("tool_not_registered")
            continue
        if step.id in seen:
            violations.append("duplicate_step_id")
        if any(dependency not in seen for dependency in step.depends_on):
            violations.append("invalid_or_forward_dependency")
        if step.requires_confirmation != spec.requires_confirmation:
            violations.append("confirmation_policy_mismatch")
        if not spec.read_only:
            violations.append("direct_write_tool_forbidden")
        seen.add(step.id)
        tool_by_id[step.id] = step.tool

    for step in plan.steps:
        if step.tool in {"recommendation.generate", "weekly_summary.generate"}:
            dependencies = {tool_by_id.get(item) for item in step.depends_on}
            if not {"context.load", "knowledge.retrieve"} <= dependencies:
                violations.append("personalized_generation_missing_dependencies")
    confirmation_ids = {step.id for step in plan.steps if step.tool.endswith(".parse_candidate")}
    if confirmation_ids:
        first_non_confirmation = next(
            (index for index, step in enumerate(plan.steps) if not step.requires_confirmation),
            len(plan.steps),
        )
        if any(step.requires_confirmation for step in plan.steps[first_non_confirmation:]):
            violations.append("confirmation_steps_must_be_a_prefix")
        for step in plan.steps:
            if step.tool == "context.load" and not confirmation_ids <= set(step.depends_on):
                violations.append("post_confirmation_context_missing_dependencies")
    return PolicyDecision(not violations, tuple(dict.fromkeys(violations)))
