import uuid

from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, Page
from app.schemas.records import WeightRecordCreate, WeightRecordResponse, WeightRecordUpdate
from app.services import records as record_service
from app.services.common import (
    commit_idempotent_or_replay,
    find_idempotent_response,
    store_idempotent_response,
)

router = APIRouter(prefix="/weight-records", tags=["Weight Records"])


@router.get("", response_model=Page[WeightRecordResponse])
def list_records(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return record_service.list_weight(db, user, limit, offset)


@router.post("", response_model=WeightRecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: WeightRecordCreate,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = payload.model_dump(mode="json")
    replay = find_idempotent_response(
        db, user_id=user.id, method="POST", path=request.url.path, key=idempotency_key, payload=body
    )
    if replay is not None:
        return replay
    record = record_service.create_weight(db, user, payload, request.state.request_id)
    response = WeightRecordResponse.model_validate(record).model_dump(mode="json")
    store_idempotent_response(
        db,
        user_id=user.id,
        method="POST",
        path=request.url.path,
        key=idempotency_key,
        payload=body,
        status_code=201,
        response_body=response,
    )
    return (
        commit_idempotent_or_replay(
            db,
            user_id=user.id,
            method="POST",
            path=request.url.path,
            key=idempotency_key,
            payload=body,
        )
        or response
    )


@router.patch("/{record_id}", response_model=WeightRecordResponse)
def update_record(
    record_id: uuid.UUID,
    payload: WeightRecordUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return record_service.update_weight(db, user, record_id, payload, request.state.request_id)


@router.delete("/{record_id}", response_model=MessageResponse)
def delete_record(
    record_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record_service.delete_weight(db, user, record_id, request.state.request_id)
    return MessageResponse(message="Weight record deleted")
