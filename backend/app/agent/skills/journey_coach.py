from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Literal

from app.schemas.agent import (
    AgentCoachAction,
    AgentCoachFinding,
    AgentSummaryGenerated,
    AgentSummaryPeriodStatistics,
    AgentSummaryStatistics,
)
from app.schemas.aggregates import JourneyDay

SummaryPeriod = Literal[7, 30]
SKILL_NAME = "journey_coach"
SKILL_VERSION = "1.0.0"


def _selected_period(
    statistics: AgentSummaryStatistics, period_days: SummaryPeriod
) -> AgentSummaryPeriodStatistics:
    return statistics.last_7_days if period_days == 7 else statistics.last_30_days


def _window_signals(
    days: list[JourneyDay], statistics: AgentSummaryPeriodStatistics
) -> dict[str, object]:
    included = [item for item in days if statistics.start_date <= item.date <= statistics.end_date]
    food_days = [item for item in included if item.food_records]
    activity_days = [item for item in included if item.activity_records]
    food_records = [record for item in included for record in item.food_records]
    activity_records = [record for item in included for record in item.activity_records]
    meal_counts = Counter(record.meal_type for record in food_records)
    intensity_counts = Counter(record.intensity for record in activity_records)
    return {
        "period_days": statistics.period_days,
        "record_days": statistics.days_with_records,
        "record_count": statistics.record_count,
        "food_days": len(food_days),
        "food_records": len(food_records),
        "days_with_at_least_two_meals": sum(1 for item in food_days if len(item.food_records) >= 2),
        "average_intake_kcal_on_food_days": (
            round(mean(item.intake_kcal for item in food_days), 1) if food_days else None
        ),
        "meal_counts": {
            meal: meal_counts.get(meal, 0)
            for meal in ("breakfast", "lunch", "dinner", "snack", "other")
        },
        "activity_days": len(activity_days),
        "activity_sessions": len(activity_records),
        "activity_minutes": sum(record.duration_minutes for record in activity_records),
        "moderate_or_high_sessions": sum(
            intensity_counts.get(level, 0) for level in ("moderate", "high")
        ),
        "weight_measurements": statistics.weight_count,
        "weight_change_kg": statistics.weight_change_kg,
    }


def build_coach_signals(
    days: list[JourneyDay],
    statistics: AgentSummaryStatistics,
    period_days: SummaryPeriod,
) -> dict[str, object]:
    goal = statistics.goal
    return {
        "skill": {"name": SKILL_NAME, "version": SKILL_VERSION},
        "period": _window_signals(days, _selected_period(statistics, period_days)),
        "recent_7_days": _window_signals(days, statistics.last_7_days),
        "goal": (
            {
                "kind": goal.kind,
                "daily_energy_target_kcal": goal.daily_energy_target_kcal,
                "target_weight_kg": goal.target_weight_kg,
            }
            if goal
            else None
        ),
    }


def _goal_label(statistics: AgentSummaryStatistics) -> str:
    if statistics.goal is None:
        return "当前目标"
    return {"lose_fat": "减脂", "gain_muscle": "增肌", "maintain": "保持"}[statistics.goal.kind]


def deterministic_coaching_content(
    statistics: AgentSummaryStatistics,
    signals: dict[str, object],
    period_days: SummaryPeriod,
) -> AgentSummaryGenerated:
    period = signals["period"]
    recent = signals["recent_7_days"]
    assert isinstance(period, dict)
    assert isinstance(recent, dict)
    period_label = f"近{period_days}天"
    goal_label = _goal_label(statistics)
    record_days = int(period["record_days"])
    food_days = int(period["food_days"])
    complete_food_days = int(period["days_with_at_least_two_meals"])
    average_intake = period["average_intake_kcal_on_food_days"]
    activity_sessions = int(period["activity_sessions"])
    activity_minutes = int(period["activity_minutes"])
    moderate_sessions = int(period["moderate_or_high_sessions"])
    weight_measurements = int(period["weight_measurements"])
    recent_activity_sessions = int(recent["activity_sessions"])
    recent_activity_minutes = int(recent["activity_minutes"])

    headline = (
        f"{period_label}先别急着调整热量：未来7天把记录提高到5天，"
        f"同时完成3次有计划的活动，再判断{goal_label}策略。"
    )
    intake_evidence = (
        f"{period_label}饮食只覆盖{food_days}天，其中{complete_food_days}天记录了至少2餐；"
        f"有饮食记录日平均{average_intake:g} kcal。"
        if isinstance(average_intake, int | float)
        else f"{period_label}还没有足够的饮食记录。"
    )
    activity_title = "运动已经启动，但需要固定节奏" if activity_sessions else "运动还没有形成记录"
    activity_interpretation = (
        "下一步应先稳定每周次数和分钟数，不必追求单次消耗数字越来越高。"
        if activity_sessions
        else "先从低门槛的固定时段开始，比一次安排过多运动更容易执行。"
    )
    findings = [
        AgentCoachFinding(
            title="当前第一问题是样本不完整",
            evidence=(f"{period_label}只有{record_days}个记录日；{intake_evidence}"),
            interpretation=(
                "这些数字更可能反映漏记，而不是真实日均摄入；现在继续压低热量可能做出错误调整。"
            ),
        ),
        AgentCoachFinding(
            title=activity_title,
            evidence=(
                f"{period_label}记录{activity_sessions}次活动、共{activity_minutes}分钟，"
                f"其中中高强度{moderate_sessions}次。"
            ),
            interpretation=activity_interpretation,
        ),
    ]
    if statistics.goal is not None:
        weight_change = period["weight_change_kg"]
        weight_evidence = f"{period_label}共有{weight_measurements}次称重记录"
        if isinstance(weight_change, int | float):
            weight_evidence += f"，同周期首末变化{weight_change:+g} kg"
        findings.append(
            AgentCoachFinding(
                title=f"{goal_label}进展需要同条件体重趋势",
                evidence=f"{weight_evidence}。",
                interpretation=(
                    "固定条件的两次以上称重能建立趋势基线，单次或零次记录不用于修改计划。"
                ),
            )
        )

    actions = [
        AgentCoachAction(
            title="先补齐可判断的数据",
            plan="未来7天至少记录5天；每个记录日至少覆盖2餐，并在当天21:30前补齐。",
            reason=(
                f"目前{period_label}仅{record_days}个记录日，直接用总热量调整目标容易被漏记误导。"
            ),
            success_metric="7天后：记录日≥5天，其中至少4天记录≥2餐。",
        ),
        AgentCoachAction(
            title="把运动排进日历",
            plan=(
                "未来7天安排3次活动：2次30–45分钟中等强度，1次20–30分钟轻松活动；"
                "相邻中高强度活动至少间隔1天。"
            ),
            reason=(
                (
                    f"近7天已有{recent_activity_sessions}次、{recent_activity_minutes}分钟，"
                    "在现有基础上固定频率比追求单次热量更容易持续。"
                )
                if recent_activity_sessions
                else "近7天尚无运动记录，从3次轻中等活动开始能建立可执行的周节奏。"
            ),
            success_metric="7天后：完成3次活动，总时长≥80分钟。",
        ),
    ]
    if statistics.goal is not None and weight_measurements < 2:
        actions.append(
            AgentCoachAction(
                title="建立体重趋势基线",
                plan="本周选择2个不相邻的早晨，起床如厕后、进食前各称重1次。",
                reason=f"{period_label}只有{weight_measurements}次称重，暂时缺少可比较的同条件数据。",
                success_metric="7天后：获得2次同条件体重记录，只比较趋势、不追逐单日波动。",
            )
        )
    else:
        actions.append(
            AgentCoachAction(
                title="让主餐更容易复盘",
                plan="未来7天任选4天，在至少2顿主餐中同时记录蛋白质来源和蔬菜。",
                reason="只有热量数字无法判断饮食结构；增加这两个字段才能给出下一轮结构建议。",
                success_metric="7天后：至少4天留下2顿包含蛋白质来源与蔬菜的主餐记录。",
            )
        )
    return AgentSummaryGenerated(
        headline=headline,
        key_findings=findings,
        next_7_days=actions,
        cited_chunk_ids=[],
    )


def requires_coaching_fallback(
    generated: AgentSummaryGenerated, period_days: SummaryPeriod
) -> bool:
    text_parts = [generated.headline]
    for finding in generated.key_findings:
        text_parts.extend((finding.title, finding.evidence, finding.interpretation))
        if not any(character.isdigit() for character in finding.evidence):
            return True
    for action in generated.next_7_days:
        text_parts.extend((action.title, action.plan, action.reason, action.success_metric))
        if not any(character.isdigit() for character in action.plan) or not any(
            character.isdigit() for character in action.success_metric
        ):
            return True
    if f"近{period_days}天" not in generated.headline:
        return True
    vague_phrases = ("无法评估", "继续保持", "选择一个小调整", "更容易被看见")
    if any(phrase in item for item in text_parts for phrase in vague_phrases):
        return True
    return period_days == 7 and any("近30天" in item for item in text_parts)
