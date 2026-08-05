from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentAuth, get_current_auth, get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, request: Request, db: Session = Depends(get_db)
) -> TokenResponse:
    return auth_service.register(db, payload, request.state.request_id)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    return auth_service.login(db, payload.identifier, payload.password, request.state.request_id)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest, request: Request, db: Session = Depends(get_db)
) -> TokenResponse:
    return auth_service.refresh(db, payload.refresh_token, request.state.request_id)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    auth: CurrentAuth = Depends(get_current_auth),
    db: Session = Depends(get_db),
) -> MessageResponse:
    auth_service.logout(db, auth.session, auth.user, request.state.request_id)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return auth_service.user_response(user)
