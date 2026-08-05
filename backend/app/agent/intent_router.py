import json
import re

from app.agent.model_router import ModelInvocation, ModelRouter
from app.schemas.agent import IntentItem, IntentPlan

ROUTER_PROMPT_VERSION = "intent-router-1.0.1"
ROUTER_SYSTEM_PROMPT = (
    "你是 Journey 意图路由器。只输出 schema；允许多意图；低置信度必须 clarify；"
    "不得执行写入。查询已有的身高、体重、目标或个人资料属于 profile；只有用户提供明确"
    "体重数值并表达记录或称重时才属于 weight。Prompt version: " + ROUTER_PROMPT_VERSION
)


def _detect(segment: str) -> list[IntentItem]:
    items: list[IntentItem] = []

    def add(intent: str, confidence: float) -> None:
        if not any(item.intent == intent for item in items):
            items.append(IntentItem(intent=intent, confidence=confidence, segment=segment))

    if re.search(r"(周总结|本周总结|这一周|过去一周)", segment):
        add("weekly_summary", 0.98)
    if re.search(r"(建议|推荐|今天怎么吃|今天怎么安排|计划)", segment):
        add("recommendation", 0.92)
    if re.search(r"(我的身高|我的体重|我的目标|我的画像|个人资料)", segment):
        add("profile", 0.95)
    if re.search(r"(历史|最近记录|趋势|过去几天|Journey|journey)", segment):
        add("history", 0.94)
    if re.search(r"(体重|称重|称了)\s*(?:是|为)?\s*\d{2,3}(?:\.\d+)?", segment):
        add("weight", 0.99)
    if re.search(r"(跑|走|散步|游泳|骑车|瑜伽|训练|运动|健身|跳绳|核心|拉伸|冲刺)", segment):
        add("activity", 0.96)
    if re.search(r"(吃|喝|早餐|午餐|晚餐|加餐|夜宵|米饭|面|鸡|蛋|奶|咖啡|水果)", segment):
        add("food", 0.95)
    if re.search(
        r"(蛋白|营养|补水|喝水|睡眠|恢复|热量|健康|疼痛|药|疾病|孕)", segment
    ) and re.search(r"(吗|么|如何|怎么|为什么|影响|多少|知识|咨询|？|\?)", segment):
        add("knowledge", 0.91)
    if any(item.intent == "knowledge" for item in items) and not re.search(
        r"(吃了|喝了|早餐|午餐|晚餐|加餐|夜宵)", segment
    ):
        items = [item for item in items if item.intent != "food"]
    if any(item.intent == "knowledge" for item in items) and not re.search(
        r"(做了|完成|运动了|训练了|\d+\s*(?:分钟|min))", segment
    ):
        items = [item for item in items if item.intent != "activity"]
    if any(item.intent == "history" for item in items) and not re.search(
        r"(做了|完成|运动了|训练了|跑了|走了|\d+\s*(?:分钟|min))", segment
    ):
        items = [item for item in items if item.intent != "activity"]
    if any(item.intent == "recommendation" for item in items) and not re.search(
        r"(吃了|喝了|做了|完成|\d+\s*(?:分钟|min|千卡|大卡|kcal))", segment, re.I
    ):
        items = [item for item in items if item.intent not in {"food", "activity", "weight"}]
    if re.search(r"(疾病|药|处方|胸痛|晕厥|孕期|进食障碍)", segment):
        items = [item for item in items if item.intent == "knowledge"]
        add("knowledge", 0.99)
    return items


def deterministic_intent_plan(message: str, memory_context: list[dict] | None = None) -> IntentPlan:
    segments = [
        item.strip(" ，,")
        for item in re.split(r"(?:然后|并且|以及|；|;|。|\n)+", message.strip())
        if item.strip(" ，,")
    ]
    intents: list[IntentItem] = []
    for segment in segments or [message.strip()]:
        intents.extend(_detect(segment))
    if (
        not intents
        and memory_context
        and re.search(r"(那|那么|接下来|继续|怎么调整|怎么办|给个建议)", message)
    ):
        intents.append(
            IntentItem(intent="recommendation", confidence=0.75, segment=message.strip())
        )
    if not intents:
        return IntentPlan(
            intents=[IntentItem(intent="clarify", confidence=0.35, segment=message.strip())],
            needs_clarification=True,
            clarification_question="你想记录饮食/运动/体重，查询历史，还是获取一般健康建议？",
        )
    return IntentPlan(intents=intents)


def route_intents(
    model_router: ModelRouter,
    message: str,
    memory_context: list[dict] | None = None,
) -> tuple[IntentPlan, ModelInvocation]:
    def fallback() -> IntentPlan:
        return deterministic_intent_plan(message, memory_context)

    invocation = model_router.generate(
        "intent_classification",
        IntentPlan,
        system_prompt=ROUTER_SYSTEM_PROMPT,
        user_prompt=(
            message
            if not memory_context
            else json.dumps(
                {"message": message, "recent_thread_memory": memory_context},
                ensure_ascii=False,
            )
        ),
        fallback_factory=fallback,
    )
    return IntentPlan.model_validate(invocation.output), invocation
