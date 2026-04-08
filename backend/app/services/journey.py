from collections import defaultdict
from datetime import date
from typing import List, Optional

from app.models.activity_record import ActivityRecord
from app.models.food_record import FoodRecord


WEEKDAY_MAP = {
    0: "周一",
    1: "周二",
    2: "周三",
    3: "周四",
    4: "周五",
    5: "周六",
    6: "周日",
}


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


def format_signed_kcal(value: float, record_type: str) -> str:
    abs_value = abs(float(value or 0))
    if record_type == "activity":
        return f"-{abs_value:g} kcal"
    return f"+{abs_value:g} kcal"


def build_day_status(calorie_balance: float) -> dict:
    num = float(calorie_balance or 0)
    abs_num = abs(num)

    if num < 0:
        return {
            "statusText": f"热量缺口 -{abs_num:g} kcal",
            "statusType": "done",
            "mascotType": "cheer",
            "summary": "今天整体消耗高于摄入，记录得很好，继续保持现在的节奏。",
        }

    if num == 0:
        return {
            "statusText": "完成目标",
            "statusType": "done",
            "mascotType": "cheer",
            "summary": "今天控制得很好，继续保持现在的节奏。",
        }

    if num > 500:
        return {
            "statusText": f"热量超出 +{num:g} kcal",
            "statusType": "warning",
            "mascotType": "remind",
            "summary": "今天摄入偏高，明天可以适当增加活动或减少额外零食。",
        }

    return {
        "statusText": f"热量盈余 +{num:g} kcal",
        "statusType": "positive",
        "mascotType": "base",
        "summary": "今天整体还算平衡，继续记录饮食和活动，方便后续给你更准确建议。",
    }


def build_food_item(record: FoodRecord) -> dict:
    return {
        "id": record.id,
        "meal": record.meal,
        "detail": record.detail,
        "location": record.location or "未填写",
        "kcal": format_signed_kcal(record.kcal, "food"),
        "time": record.time_text,
    }


def build_activity_item(record: ActivityRecord) -> dict:
    return {
        "id": record.id,
        "name": record.name,
        "location": record.location or "未填写",
        "kcal": format_signed_kcal(record.kcal, "activity"),
        "time": record.time_text,
    }


def build_journey_days(
    food_records: List[FoodRecord],
    activity_records: List[ActivityRecord],
    limit: int = 30,
) -> List[dict]:
    grouped = defaultdict(
        lambda: {
            "foodItems": [],
            "activityItems": [],
            "intakeKcal": 0.0,
            "activityKcal": 0.0,
        }
    )

    for record in food_records:
        grouped[record.record_date]["foodItems"].append(build_food_item(record))
        grouped[record.record_date]["intakeKcal"] += float(record.kcal or 0)

    for record in activity_records:
        grouped[record.record_date]["activityItems"].append(build_activity_item(record))
        grouped[record.record_date]["activityKcal"] += float(record.kcal or 0)

    sorted_dates = sorted(grouped.keys(), reverse=True)
    result = []

    for record_date in sorted_dates[:limit]:
        day_data = grouped[record_date]

        day_data["foodItems"].sort(
            key=lambda item: parse_time_to_minutes(item.get("time")),
            reverse=True,
        )
        day_data["activityItems"].sort(
            key=lambda item: parse_time_to_minutes(item.get("time")),
            reverse=True,
        )

        intake_kcal = round(day_data["intakeKcal"], 2)
        activity_kcal = round(day_data["activityKcal"], 2)
        calorie_balance = round(intake_kcal - activity_kcal, 2)

        status = build_day_status(calorie_balance)

        result.append(
            {
                "id": record_date.isoformat(),
                "record_date": record_date,
                "date": f"{record_date.month}月{record_date.day}日",
                "weekday": WEEKDAY_MAP[record_date.weekday()],
                "statusText": status["statusText"],
                "statusType": status["statusType"],
                "summary": status["summary"],
                "mascotType": status["mascotType"],
                "intakeKcal": intake_kcal,
                "activityKcal": activity_kcal,
                "calorieBalance": calorie_balance,
                "foodItems": day_data["foodItems"],
                "activityItems": day_data["activityItems"],
            }
        )

    return result