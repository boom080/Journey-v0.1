from datetime import date

from sqlalchemy.orm import Session

from app.models.activity_record import ActivityRecord
from app.models.food_record import FoodRecord
from app.models.user import User


GOAL_SUGGESTIONS = {
    "减脂": "今天节奏不错，继续稳定记录吃了什么和做了什么。",
    "增肌": "记住把饮食和训练一起记录，首页会更容易给出有用建议。",
    "维持": "继续轻量记录今天的饮食和活动，保持真实生活节奏。"
}


def build_home_summary(db: Session, user: User) -> dict:
    today = date.today()

    food_records = (
        db.query(FoodRecord)
        .filter(FoodRecord.user_id == user.id, FoodRecord.record_date == today)
        .order_by(FoodRecord.created_at.desc())
        .all()
    )
    activity_records = (
        db.query(ActivityRecord)
        .filter(ActivityRecord.user_id == user.id, ActivityRecord.record_date == today)
        .order_by(ActivityRecord.created_at.desc())
        .all()
    )

    updates = []
    for item in food_records[:2]:
        updates.append(
            {
                "title": item.meal,
                "description": item.detail,
                "time_text": item.time_text,
                "kcal": f"+{item.kcal:g} kcal",
            }
        )

    for item in activity_records[:2]:
        updates.append(
            {
                "title": item.name,
                "description": item.location or "已记录活动",
                "time_text": item.time_text,
                "kcal": f"-{item.kcal:g} kcal",
            }
        )

    updates.sort(key=lambda item: item.get("time_text") or "", reverse=True)

    intake = sum(float(item.kcal or 0) for item in food_records)
    activity = sum(float(item.kcal or 0) for item in activity_records)
    net = round(intake - activity, 2)
    has_today_data = bool(food_records or activity_records)

    if has_today_data:
        today_summary = (
            f"今天已记录 {len(food_records)} 条饮食、{len(activity_records)} 条活动，"
            f"摄入 {intake:g} kcal，消耗 {activity:g} kcal。"
        )
    else:
        today_summary = "今天还没有记录，先记下吃了什么或做了什么。"

    return {
        "today_date": today.isoformat(),
        "today_summary": today_summary,
        "goal_suggestion": GOAL_SUGGESTIONS.get(user.goal, GOAL_SUGGESTIONS["维持"]),
        "intake_kcal": round(intake, 2),
        "activity_kcal": round(activity, 2),
        "net_kcal": net,
        "recent_updates": updates[:4],
        "extra": {
            "goal": user.goal,
            "record_counts": {
                "food": len(food_records),
                "activity": len(activity_records),
            },
            "source_types": ["manual", "ai", "image", "ocr"],
        },
    }
