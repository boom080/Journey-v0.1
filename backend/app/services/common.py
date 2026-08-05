import hashlib
import json
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.models.audit import AuditEvent
from app.models.idempotency import IdempotencyKey


def user_local_date(value: datetime, timezone_name: str) -> date:
    return value.astimezone(ZoneInfo(timezone_name)).date()


def add_audit(
    db: Session,
    *,
    user_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None,
    request_id: str,
    event_data: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditEvent(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            request_id=request_id,
            event_data=event_data or {},
        )
    )


def _payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def find_idempotent_response(
    db: Session,
    *,
    user_id: uuid.UUID,
    method: str,
    path: str,
    key: str | None,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    if key is None:
        return None
    if not key.strip() or len(key) > 128:
        raise APIError(
            status_code=400,
            code="invalid_idempotency_key",
            message="Idempotency-Key must be 1-128 characters",
        )
    record = db.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == user_id,
            IdempotencyKey.method == method,
            IdempotencyKey.path == path,
            IdempotencyKey.key == key,
        )
    )
    if record is None:
        return None
    if record.request_hash != _payload_hash(payload):
        raise APIError(
            status_code=409,
            code="idempotency_conflict",
            message="Idempotency-Key was already used with a different payload",
        )
    return record.response_body


def store_idempotent_response(
    db: Session,
    *,
    user_id: uuid.UUID,
    method: str,
    path: str,
    key: str | None,
    payload: dict[str, Any],
    status_code: int,
    response_body: dict[str, Any],
) -> None:
    if key is None:
        return
    db.add(
        IdempotencyKey(
            user_id=user_id,
            method=method,
            path=path,
            key=key,
            request_hash=_payload_hash(payload),
            response_status=status_code,
            response_body=response_body,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
    )


def commit_idempotent_or_replay(
    db: Session,
    *,
    user_id: uuid.UUID,
    method: str,
    path: str,
    key: str | None,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        db.commit()
        return None
    except IntegrityError:
        db.rollback()
        replay = find_idempotent_response(
            db,
            user_id=user_id,
            method=method,
            path=path,
            key=key,
            payload=payload,
        )
        if replay is not None:
            return replay
        raise
