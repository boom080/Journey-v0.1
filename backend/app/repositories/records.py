import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.database import Base


def get_owned[ModelT: Base](
    db: Session, model: type[ModelT], user_id: uuid.UUID, record_id: uuid.UUID
) -> ModelT | None:
    return db.scalar(select(model).where(model.id == record_id, model.user_id == user_id))


def list_owned[ModelT: Base](
    db: Session,
    model: type[ModelT],
    user_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
    order_column,
) -> tuple[list[ModelT], int]:
    base: Select = select(model).where(model.user_id == user_id)
    items = list(
        db.scalars(base.order_by(order_column.desc(), model.id.desc()).limit(limit).offset(offset))
    )
    total = int(
        db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id)) or 0
    )
    return items, total
