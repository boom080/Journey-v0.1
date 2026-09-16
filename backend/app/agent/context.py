import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.aggregates import home_today, journey
from app.services.profile import get_active_goal, get_profile

CONTEXT_VERSION = "journey-context-1.0.0"
DEFAULT_CONTEXT_TOKEN_BUDGET = 1800


def _weight_change_kg(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return round(values[-1] - values[0], 2)


@dataclass(frozen=True)
class ContextSnapshot:
    version: str
    estimated_tokens: int
    data: dict
    included_sources: list[str]


def build_context(
    db: Session,
    user: User,
    *,
    token_budget: int = DEFAULT_CONTEXT_TOKEN_BUDGET,
    range_days: int = 7,
) -> ContextSnapshot:
    range_days = max(1, min(range_days, 30))
    profile = get_profile(db, user)
    goal = get_active_goal(db, user.id)
    today = home_today(db, user, None)
    today_date = datetime.now(UTC).astimezone(ZoneInfo(profile.timezone)).date()
    recent = journey(
        db,
        user,
        start_date=today_date - timedelta(days=range_days - 1),
        end_date=today_date,
        cursor=None,
        limit=range_days,
    )
    weights = sorted(
        [record for day in recent.items for record in day.weight_records],
        key=lambda record: record.measured_at,
    )
    weight_values = [float(record.weight_kg) for record in weights]
    first_weight = weight_values[0] if len(weight_values) >= 2 else None
    latest_weight = weight_values[-1] if weight_values else None
    weight_change = _weight_change_kg(weight_values)
    total_intake = round(sum(item.intake_kcal for item in recent.items), 2)
    total_activity = round(sum(item.activity_kcal for item in recent.items), 2)
    daily_resting = today.resting_energy.kcal_per_day
    range_resting = round(daily_resting * range_days, 2) if daily_resting is not None else None
    recent_totals = {
        "days_with_records": len(recent.items),
        "range_days": range_days,
        "intake_kcal": total_intake,
        "activity_kcal": total_activity,
        "recorded_balance_kcal": round(total_intake - total_activity, 2),
        "resting_energy_kcal_per_day": daily_resting,
        "estimated_resting_energy_kcal": range_resting,
        "estimated_energy_balance_kcal": (
            round(total_intake - total_activity - range_resting, 2)
            if range_resting is not None
            else None
        ),
        "energy_estimate_status": today.resting_energy.status,
        "energy_estimate_note": today.resting_energy.note,
        "average_daily_intake_kcal": round(total_intake / range_days, 2),
        "average_daily_activity_kcal": round(total_activity / range_days, 2),
        "food_count": sum(len(item.food_records) for item in recent.items),
        "activity_count": sum(len(item.activity_records) for item in recent.items),
        "weight_count": sum(len(item.weight_records) for item in recent.items),
        "first_weight_kg": first_weight,
        "latest_weight_kg": latest_weight,
        "weight_change_kg": weight_change,
    }
    data = {
        "range_days": range_days,
        "profile": {
            "timezone": profile.timezone,
            "sex": profile.sex,
            "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
            "height_cm": profile.height_cm,
            "preferred_unit": profile.preferred_unit,
            "latest_weight_kg": profile.latest_weight_kg,
        },
        "goal": (
            {
                "kind": goal.kind,
                "target_weight_kg": float(goal.target_weight_kg)
                if goal.target_weight_kg is not None
                else None,
                "daily_energy_target_kcal": float(goal.daily_energy_target_kcal)
                if goal.daily_energy_target_kcal is not None
                else None,
            }
            if goal
            else None
        ),
        "today": today.model_dump(mode="json"),
        "recent_totals": recent_totals,
    }
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    estimated_tokens = max(1, (len(serialized) + 2) // 3)
    if estimated_tokens > token_budget:
        data.pop("recent_totals", None)
        serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        estimated_tokens = max(1, (len(serialized) + 2) // 3)
    return ContextSnapshot(
        version=CONTEXT_VERSION,
        estimated_tokens=estimated_tokens,
        data=data,
        included_sources=["profile", "goal", "home_today", "recent_aggregates"],
    )
