import json

from app.agent.model_router import ModelInvocation, ModelRouter
from app.agent.specialists import public_specialist_catalog, specialist_for_tool
from app.agent.tool_registry import public_tool_catalog
from app.schemas.agent import AgentPlan, AgentPlanStep, IntentPlan

PLAN_PROMPT_VERSION = "journey-agent-planner-3.0.0"
PLAN_SYSTEM_PROMPT = (
    "你是 Journey 的受控任务规划器。只输出 AgentPlan Schema；只能选择提供的工具；"
    "最多 6 步；依赖必须引用更早步骤；饮食、运动、体重只能生成候选并标记需要用户确认；"
    "不得规划诊断、处方、后台自主任务或任何直接写库工具。严格遵循最小计划："
    "food 只用 food.parse_candidate；activity 只用 activity.parse_candidate；"
    "weight 只用 weight.parse_candidate；profile 只用 profile.read；history 只用 journey.read；"
    "knowledge 只用 knowledge.answer；recommendation 恰好使用 context.load、knowledge.retrieve、"
    "recommendation.generate，且 generate 的 depends_on 必须同时引用前两个步骤；weekly_summary"
    "同理使用 context.load、knowledge.retrieve、weekly_summary.generate。混合意图按识别顺序合并，"
    "context.load 和 knowledge.retrieve 最多各出现一次。没有 history 意图不得添加 journey.read；"
    "除 recommendation/weekly_summary 外不得添加 context.load。"
    "若同一请求既要生成写入候选又要生成个性化建议或周总结，所有写入候选必须排在前面，"
    "context.load 必须依赖全部候选步骤，以便系统暂停并等待用户确认后再继续。"
    "不要添加任何看似有帮助但非必需的步骤。"
    f" Prompt version: {PLAN_PROMPT_VERSION}"
)


def deterministic_plan(message: str, intent_plan: IntentPlan) -> AgentPlan:
    steps: list[AgentPlanStep] = []
    reused: dict[str, str] = {}
    truncated = False

    def add(
        tool: str,
        reason: str,
        *,
        segment: str | None = None,
        depends_on: list[str] | None = None,
        requires_confirmation: bool = False,
        reuse: bool = False,
    ) -> str | None:
        nonlocal truncated
        if reuse and tool in reused:
            return reused[tool]
        if len(steps) >= 6:
            truncated = True
            return None
        step_id = f"step-{len(steps) + 1}"
        steps.append(
            AgentPlanStep(
                id=step_id,
                tool=tool,
                reason=reason,
                segment=segment,
                depends_on=[item for item in (depends_on or []) if item],
                requires_confirmation=requires_confirmation,
                specialist=specialist_for_tool(tool),
            )
        )
        if reuse:
            reused[tool] = step_id
        return step_id

    ordered_items = sorted(
        intent_plan.intents,
        key=lambda item: 0 if item.intent in {"food", "activity", "weight"} else 1,
    )
    confirmation_step_ids: list[str] = []
    for item in ordered_items:
        if item.intent in {"food", "activity", "weight"}:
            step_id = add(
                f"{item.intent}.parse_candidate",
                f"把 {item.intent} 内容解析为用户可校正的结构化候选",
                segment=item.segment,
                requires_confirmation=True,
            )
            if step_id:
                confirmation_step_ids.append(step_id)
        elif item.intent == "profile":
            add("profile.read", "读取当前用户画像以回答查询", reuse=True)
        elif item.intent == "history":
            add("journey.read", "读取近期记录以回答历史查询", reuse=True)
        elif item.intent == "knowledge":
            add(
                "knowledge.answer",
                "从受控知识库检索证据并生成带引用的回答",
                segment=item.segment,
            )
        elif item.intent in {"recommendation", "weekly_summary"}:
            context_id = add(
                "context.load",
                "在候选确认后加载画像、目标和近期聚合",
                segment=item.segment,
                depends_on=confirmation_step_ids,
                reuse=True,
            )
            retrieve_id = add(
                "knowledge.retrieve",
                "检索与饮食、运动和恢复相关的受控知识",
                segment=(
                    "均衡饮食 运动恢复 睡眠 安全"
                    if item.intent == "recommendation"
                    else "每周健康记录 饮食 运动 恢复"
                ),
                reuse=True,
            )
            add(
                f"{item.intent}.generate",
                "综合结构化上下文和受控知识生成结果",
                depends_on=[item for item in (context_id, retrieve_id) if item],
            )

    needs_clarification = intent_plan.needs_clarification or truncated
    clarification = intent_plan.clarification_question
    if not steps:
        add("context.load", "为澄清问题加载最小上下文")
        needs_clarification = True
        clarification = clarification or "你想记录饮食、运动、体重，还是查询历史或建议？"
    if truncated:
        clarification = "这次请求包含过多独立任务，请确认最优先处理的内容。"
    intent_names = "、".join(item.intent for item in intent_plan.intents)
    return AgentPlan(
        goal=f"处理已识别的 {intent_names or 'clarify'} 任务",
        steps=steps,
        needs_clarification=needs_clarification,
        clarification_question=clarification,
    )


def create_plan(
    model_router: ModelRouter,
    *,
    message: str,
    intent_plan: IntentPlan,
    memory_context: list[dict] | None = None,
) -> tuple[AgentPlan, ModelInvocation]:
    def fallback() -> AgentPlan:
        return deterministic_plan(message, intent_plan)

    invocation = model_router.generate(
        "task_planning",
        AgentPlan,
        system_prompt=PLAN_SYSTEM_PROMPT,
        user_prompt=json.dumps(
            {
                "message": message,
                "intents": intent_plan.model_dump(mode="json"),
                "recent_thread_memory": memory_context or [],
                "tools": public_tool_catalog(),
                "specialists": public_specialist_catalog(),
            },
            ensure_ascii=False,
        ),
        fallback_factory=fallback,
    )
    return AgentPlan.model_validate(invocation.output), invocation


def redacted_plan(plan: AgentPlan) -> AgentPlan:
    tools = "、".join(step.tool for step in plan.steps)
    return plan.model_copy(
        update={
            "goal": f"执行已校验的工具计划：{tools}",
            "steps": [
                step.model_copy(
                    update={"segment": None, "specialist": specialist_for_tool(step.tool)}
                )
                for step in plan.steps
            ],
        }
    )
