import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.settings import get_settings
from app.models.user import User
from app.schemas.common import MessageResponse, Page
from app.schemas.inspirations import (
    InspirationCreateRequest,
    InspirationPreviewRequest,
    InspirationPreviewResponse,
    InspirationResponse,
)
from app.services import inspirations as inspiration_service
from app.services.common import add_audit

router = APIRouter(prefix="/inspirations", tags=["Life Inspirations"])


@router.post("/preview", response_model=InspirationPreviewResponse)
def preview_inspiration(
    payload: InspirationPreviewRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InspirationPreviewResponse:
    result = inspiration_service.preview_public_inspiration(
        payload.source_url,
        fetch_enabled=get_settings().life_inspiration_fetch_enabled,
    )
    add_audit(
        db,
        user_id=user.id,
        action="inspiration.previewed",
        resource_type="life_inspiration",
        resource_id=None,
        request_id=request.state.request_id,
        event_data={
            "source_name": result.source_name,
            "status": result.status,
            "safety_flags": result.safety_flags,
        },
    )
    db.commit()
    return result


@router.post("", response_model=InspirationResponse, status_code=status.HTTP_201_CREATED)
def create_inspiration(
    payload: InspirationCreateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InspirationResponse:
    return InspirationResponse.model_validate(
        inspiration_service.create_inspiration(db, user, payload, request.state.request_id)
    )


@router.get("", response_model=Page[InspirationResponse])
def list_inspirations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return inspiration_service.list_inspirations(db, user, limit, offset)


@router.delete("/{inspiration_id}", response_model=MessageResponse)
def delete_inspiration(
    inspiration_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    inspiration_service.delete_inspiration(db, user, inspiration_id, request.state.request_id)
    return MessageResponse(message="Life inspiration deleted")
