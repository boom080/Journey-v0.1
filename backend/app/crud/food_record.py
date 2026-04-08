from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.food_record import FoodRecord


def create_food_record(db: Session, user_id: int, data: dict):
    record = FoodRecord(user_id=user_id, **data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_food_record_by_id(db: Session, user_id: int, record_id: int):
    return (
        db.query(FoodRecord)
        .filter(FoodRecord.id == record_id, FoodRecord.user_id == user_id)
        .first()
    )


def list_food_records(
    db: Session,
    user_id: int,
    record_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    query = db.query(FoodRecord).filter(FoodRecord.user_id == user_id)

    if record_date:
        query = query.filter(FoodRecord.record_date == record_date)

    if start_date:
        query = query.filter(FoodRecord.record_date >= start_date)

    if end_date:
        query = query.filter(FoodRecord.record_date <= end_date)

    return (
        query.order_by(FoodRecord.record_date.desc(), FoodRecord.created_at.desc())
        .all()
    )


def delete_food_record(db: Session, record: FoodRecord):
    db.delete(record)
    db.commit()


def update_food_record(db: Session, record: FoodRecord, update_data: dict):
    for key, value in update_data.items():
        setattr(record, key, value)

    db.add(record)
    db.commit()
    db.refresh(record)
    return record
