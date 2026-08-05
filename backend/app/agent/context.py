import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.aggregates import home_today, journey
from app.services.profile import get_active_goal, get_profile

CONTEXT_VERSION = "journey-context-1.0.0"
DEFAULT_CONTEXT_TOKEN_BUDGET = 1800


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
) -> ContextSnapshot:
    profile = get_profile(db, user)
    goal = get_active_goal(db, user.id)
    today = home_today(db, user, None)
    recent = journey(db, user, start_date=None, end_date=None, cursor=None, limit=7)
    recent_totals = {
        "days_with_records": len(recent.items),
        "intake_kcal": round(sum(item.intake_kcal for item in recent.items), 2),
        "activity_kcal": round(sum(item.activity_kcal for item in recent.items), 2),
        "food_count": sum(len(item.food_records) for item in recent.items),
        "activity_count": sum(len(item.activity_records) for item in recent.items),
        "weight_count": sum(len(item.weight_records) for item in recent.items),
    }
    data = {
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
