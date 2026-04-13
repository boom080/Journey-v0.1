import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps_mini import get_current_user, get_db
from app.core.security import create_access_token
from app.core.wechat import code_to_session
from app.crud.invite_code import (
    get_invite_code_by_code,
    invite_code_is_expired,
    mark_invite_code_used,
)
from app.crud.user_mini import create_user_by_openid, get_user_by_openid, update_user
from app.models.invite_code import InviteCode
from app.models.user import User
from app.schemas.auth import (
    InviteCodePayload,
    InviteVerifyRequest,
    InviteVerifyResponse,
    TokenResponse,
    UserProfilePayload,
    WechatLoginRequest,
)

router = APIRouter(prefix="/auth", tags=["Mini Auth"])
logger = logging.getLogger("journey.mini.auth")


def build_user_payload(user: User) -> UserProfilePayload:
    return UserProfilePayload(
        id=user.id,
        openid=user.openid,
        unionid=user.unionid,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        is_activated=user.is_activated,
        invite_code_id=user.invite_code_id,
        goal=user.goal,
        gender=user.gender,
        height=user.height,
        weight=user.weight,
        body_fat_rate=user.body_fat_rate,
    )


def build_invite_payload(invite_code: InviteCode) -> InviteCodePayload:
    return InviteCodePayload(
        id=invite_code.id,
        code=invite_code.code,
        status=invite_code.status,
        max_uses=invite_code.max_uses,
        used_count=invite_code.used_count,
        used_by_user_id=invite_code.used_by_user_id,
        used_by_openid=invite_code.used_by_openid,
        expires_at=invite_code.expires_at,
    )


@router.post("/wechat-login", response_model=TokenResponse)
def wechat_login(payload: WechatLoginRequest, db: Session = Depends(get_db)):
    logger.info(
        "wechat_login_request endpoint=wechat-login code_length=%s nickname_provided=%s avatar_provided=%s",
        len(payload.code or ""),
        bool(payload.nickname),
        bool(payload.avatar_url),
    )
    identity = code_to_session(payload.code)
    user = get_user_by_openid(db, identity["openid"])

    if not user:
        user = create_user_by_openid(
            db=db,
            openid=identity["openid"],
            unionid=identity.get("unionid"),
            nickname=payload.nickname,
            avatar_url=payload.avatar_url,
        )
    else:
        update_data = {"unionid": identity.get("unionid")}
        if payload.nickname:
            update_data["nickname"] = payload.nickname
        if payload.avatar_url:
            update_data["avatar_url"] = payload.avatar_url
        user = update_user(db, user, update_data)

    access_token = create_access_token({"user_id": user.id, "openid": user.openid})
    logger.info(
        "wechat_login_result endpoint=wechat-login user_id=%s is_activated=%s has_unionid=%s",
        user.id,
        user.is_activated,
        bool(user.unionid),
    )
    return TokenResponse(
        access_token=access_token,
        openid=user.openid,
        unionid=user.unionid,
        user=build_user_payload(user),
    )


@router.post("/verify-invite", response_model=InviteVerifyResponse)
def verify_invite(
    payload: InviteVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invite_code = get_invite_code_by_code(db, payload.code)
    if not invite_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邀请码不存在"
        )

    if invite_code.status == "disabled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码已停用"
        )

    if invite_code_is_expired(invite_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码已过期"
        )

    if invite_code.used_by_user_id and invite_code.used_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码已被使用"
        )

    if int(invite_code.used_count or 0) >= max(int(invite_code.max_uses or 1), 1) and invite_code.used_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请码已达到使用上限"
        )

    invite_code = mark_invite_code_used(db, invite_code, current_user.id, current_user.openid)
    user = update_user(
        db,
        current_user,
        {"is_activated": True, "invite_code_id": invite_code.id}
    )

    return InviteVerifyResponse(
        message="邀请码校验成功",
        invite_code_id=invite_code.id,
        user=build_user_payload(user),
        invite_code=build_invite_payload(invite_code),
    )


@router.get("/me", response_model=UserProfilePayload)
def get_me(current_user: User = Depends(get_current_user)):
    return build_user_payload(current_user)
