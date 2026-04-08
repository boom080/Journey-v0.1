import json
import logging
import os
from urllib.parse import urlencode
from urllib.request import urlopen

from dotenv import load_dotenv
from fastapi import HTTPException, status

load_dotenv()

logger = logging.getLogger("journey.wechat")

WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "").strip()
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "").strip()
WECHAT_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
WECHAT_REQUEST_TIMEOUT_SECONDS = int(os.getenv("WECHAT_REQUEST_TIMEOUT_SECONDS", "20") or "20")


def ensure_wechat_config():
    if WECHAT_APP_ID and WECHAT_APP_SECRET:
        return

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="微信登录配置缺失，请先设置 WECHAT_APP_ID 和 WECHAT_APP_SECRET",
    )


def code_to_session(code: str) -> dict:
    ensure_wechat_config()

    query = urlencode(
        {
            "appid": WECHAT_APP_ID,
            "secret": WECHAT_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    request_url = f"{WECHAT_CODE2SESSION_URL}?{query}"

    logger.info(
        "wechat_code2session_request endpoint=code2Session timeout_seconds=%s appid_suffix=%s",
        WECHAT_REQUEST_TIMEOUT_SECONDS,
        WECHAT_APP_ID[-6:] if WECHAT_APP_ID else "",
    )

    try:
        with urlopen(request_url, timeout=WECHAT_REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        logger.warning("wechat_code2session_error error=%s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"微信登录服务调用失败: {error}",
        ) from error

    if payload.get("errcode"):
        logger.warning(
            "wechat_code2session_business_error errcode=%s errmsg=%s",
            payload.get("errcode"),
            payload.get("errmsg"),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=payload.get("errmsg") or "微信登录失败",
        )

    if not payload.get("openid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="微信登录未返回 openid",
        )

    logger.info(
        "wechat_code2session_result has_openid=%s has_unionid=%s",
        bool(payload.get("openid")),
        bool(payload.get("unionid")),
    )
    return payload
