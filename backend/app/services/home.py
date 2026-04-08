from datetime import date

from sqlalchemy.orm import Session

from app.models.activity_record import ActivityRecord
from app.models.food_record import FoodRecord
from app.models.user import User


GOAL_SUGGESTIONS = {
    "减脂": "今天优先记录真实摄入和活动消耗，先把连续记录稳定下来。",
    "增肌": "今天关注三餐与训练后的补充，保持饮食和活动一起记录。",
    "维持": "继续轻量记录饮食和活动，让首页建议更贴近你的真实节奏。"
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
                "title": f"{item.meal} · {item.detail}",
                "description": f"饮食记录 {item.kcal:g} kcal",
                "time_text": item.time_text,
            }
        )

    for item in activity_records[:2]:
        updates.append(
            {
                "title": item.name,
                "description": f"活动记录 {item.kcal:g} kcal",
                "time_text": item.time_text,
            }
        )

    updates.sort(key=lambda item: item.get("time_text") or "", reverse=True)
    has_today_data = bool(food_records or activity_records)

    if has_today_data:
        intake = sum(float(item.kcal or 0) for item in food_records)
        activity = sum(float(item.kcal or 0) for item in activity_records)
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
        "recent_updates": updates[:4],
    }
