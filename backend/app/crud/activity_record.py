from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.activity_record import ActivityRecord


def create_activity_record(db: Session, user_id: int, data: dict):
    record = ActivityRecord(user_id=user_id, **data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_activity_record_by_id(db: Session, user_id: int, record_id: int):
    return (
        db.query(ActivityRecord)
        .filter(ActivityRecord.id == record_id, ActivityRecord.user_id == user_id)
        .first()
    )


def list_activity_records(
    db: Session,
    user_id: int,
    record_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    query = db.query(ActivityRecord).filter(ActivityRecord.user_id == user_id)

    if record_date:
        query = query.filter(ActivityRecord.record_date == record_date)

    if start_date:
        query = query.filter(ActivityRecord.record_date >= start_date)

    if end_date:
        query = query.filter(ActivityRecord.record_date <= end_date)

    return (
        query.order_by(ActivityRecord.record_date.desc(), ActivityRecord.created_at.desc())
        .all()
    )


def delete_activity_record(db: Session, record: ActivityRecord):
    db.delete(record)
    db.commit()


def update_activity_record(db: Session, record: ActivityRecord, update_data: dict):
    for key, value in update_data.items():
        setattr(record, key, value)

    db.add(record)
    db.commit()
    db.refresh(record)
    return record
