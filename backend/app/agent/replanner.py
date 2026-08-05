import json

from app.agent.model_router import ModelInvocation, ModelRouter
from app.schemas.agent import AgentObservation, AgentRecoveryDecision

REPLAN_PROMPT_VERSION = "journey-agent-replanner-1.0.0"
REPLAN_SYSTEM_PROMPT = (
    "你是 Journey 的故障恢复规划器。只能从 allowed_alternatives 中选择一个工具，"
    "不得创造工具、不得重复失败工具、不得修改用户数据；若无允许替代则 stop。"
    f" Prompt version: {REPLAN_PROMPT_VERSION}"
)


def choose_recovery(
    model_router: ModelRouter,
    observation: AgentObservation,
) -> tuple[AgentRecoveryDecision, ModelInvocation]:
    def fallback() -> AgentRecoveryDecision:
        if observation.recoverable and observation.allowed_alternatives:
            return AgentRecoveryDecision(
                action="use_alternative",
                tool=observation.allowed_alternatives[0],
                reason="使用策略白名单中的首个确定性降级工具",
            )
        return AgentRecoveryDecision(action="stop", reason="没有安全且允许的恢复工具")

    invocation = model_router.generate(
        "failure_replanning",
        AgentRecoveryDecision,
        system_prompt=REPLAN_SYSTEM_PROMPT,
        user_prompt=json.dumps(observation.model_dump(mode="json"), ensure_ascii=False),
        fallback_factory=fallback,
    )
    decision = AgentRecoveryDecision.model_validate(invocation.output)
    if (
        decision.action == "use_alternative"
        and decision.tool not in observation.allowed_alternatives
    ):
        decision = fallback()
    return decision, invocation
