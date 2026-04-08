from collections import defaultdict
from typing import List, Optional

from app.models.activity_record import ActivityRecord
from app.models.food_record import FoodRecord


def parse_time_to_minutes(value: Optional[str]) -> int:
    if not value or not isinstance(value, str):
        return -1

    parts = value.split(":")
    if len(parts) != 2:
        return -1

    try:
        hour = int(parts[0])
        minute = int(parts[1])
        return hour * 60 + minute
    except ValueError:
        return -1


def build_day_status(calorie_balance: float) -> tuple[str, str]:
    if calorie_balance < 0:
        return "今天消耗高于摄入，记录节奏很稳。", f"结余 {calorie_balance:g} kcal"
    if calorie_balance > 300:
        return "今天摄入偏高，明天可以适当补一点活动。", f"结余 +{calorie_balance:g} kcal"
    return "今天整体比较平衡，继续轻量记录就好。", f"结余 +{calorie_balance:g} kcal"


def build_food_item(record: FoodRecord) -> dict:
    return {
        "id": record.id,
        "meal": record.meal,
        "detail": record.detail,
        "location": record.location or "未填写地点",
        "kcal": round(float(record.kcal or 0), 2),
        "time_text": record.time_text,
    }


def build_activity_item(record: ActivityRecord) -> dict:
    return {
        "id": record.id,
        "name": record.name,
        "location": record.location or "未填写地点",
        "kcal": round(float(record.kcal or 0), 2),
        "time_text": record.time_text,
    }


def build_journey_days(
    food_records: List[FoodRecord],
    activity_records: List[ActivityRecord],
    limit: int = 7,
    cursor: Optional[str] = None,
) -> dict:
    grouped = defaultdict(lambda: {"foodItems": [], "activityItems": [], "intake": 0.0, "activity": 0.0})

    for record in food_records:
        grouped[record.record_date]["foodItems"].append(build_food_item(record))
        grouped[record.record_date]["intake"] += float(record.kcal or 0)

    for record in activity_records:
        grouped[record.record_date]["activityItems"].append(build_activity_item(record))
        grouped[record.record_date]["activity"] += float(record.kcal or 0)

    sorted_dates = sorted(grouped.keys(), reverse=True)
    if cursor:
        sorted_dates = [item for item in sorted_dates if item.isoformat() < cursor]

    page_dates = sorted_dates[:limit]
    items = []

    for record_date in page_dates:
        day_data = grouped[record_date]
        day_data["foodItems"].sort(key=lambda item: parse_time_to_minutes(item.get("time_text")), reverse=True)
        day_data["activityItems"].sort(key=lambda item: parse_time_to_minutes(item.get("time_text")), reverse=True)

        calorie_balance = round(day_data["intake"] - day_data["activity"], 2)
        summary, status_text = build_day_status(calorie_balance)
        items.append(
            {
                "id": record_date.isoformat(),
                "record_date": record_date,
                "summary": summary,
                "status_text": status_text,
                "foodItems": day_data["foodItems"],
                "activityItems": day_data["activityItems"],
            }
        )

    has_more = len(sorted_dates) > limit
    next_cursor = page_dates[-1].isoformat() if has_more and page_dates else None
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}
