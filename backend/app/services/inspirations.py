import html
import ipaddress
import socket
import uuid
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.models.inspiration import LifeInspiration
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.inspirations import (
    InspirationCreateRequest,
    InspirationPreviewResponse,
    InspirationResponse,
)
from app.services.common import add_audit

ALLOWED_HOSTS = frozenset(
    {"xiaohongshu.com", "www.xiaohongshu.com", "xhslink.com", "www.xhslink.com"}
)
MAX_RESPONSE_BYTES = 256 * 1024
MAX_REDIRECTS = 3
FETCH_TIMEOUT = httpx.Timeout(8.0, connect=4.0)
SUSPICIOUS_INSTRUCTIONS = (
    "ignore previous instructions",
    "ignore all previous",
    "system prompt",
    "developer message",
    "请忽略之前",
    "忽略以上指令",
    "系统提示词",
    "开发者消息",
)


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs if value is not None}
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() != "meta":
            return
        key = (attributes.get("property") or attributes.get("name") or "").lower()
        content = attributes.get("content")
        if key and content and key not in self.meta:
            self.meta[key] = content

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)


def _api_error(code: str, message: str) -> APIError:
    return APIError(status_code=422, code=code, message=message)


def normalize_public_url(raw_url: str) -> str:
    value = raw_url.strip()
    if len(value) > 2048:
        raise _api_error("inspiration_url_too_long", "The shared URL is too long")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise _api_error("invalid_inspiration_url", "The shared URL is invalid") from error
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() != "https" or not host:
        raise _api_error("inspiration_https_required", "Only HTTPS public links are accepted")
    if parsed.username or parsed.password or port not in (None, 443):
        raise _api_error("invalid_inspiration_url", "Credentials and custom ports are not accepted")
    if host not in ALLOWED_HOSTS:
        raise _api_error(
            "inspiration_domain_not_allowed",
            "Only user-shared public Xiaohongshu links are accepted in this version",
        )
    return urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))


def assert_public_dns(host: str) -> None:
    try:
        results = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise _api_error(
            "inspiration_dns_failed", "The public source could not be resolved"
        ) from error
    addresses = {item[4][0] for item in results}
    if not addresses:
        raise _api_error("inspiration_dns_failed", "The public source could not be resolved")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise _api_error(
                "inspiration_ssrf_blocked", "Private or local network targets are blocked"
            )


def _clean_text(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(html.unescape(value).split())
    return cleaned[:limit] or None


def _manual_preview(
    source_url: str,
    message: str,
    *flags: str,
) -> InspirationPreviewResponse:
    return InspirationPreviewResponse(
        status="manual_required",
        source_url=source_url,
        title=None,
        summary=None,
        source_checked_at=datetime.now(UTC),
        safety_flags=["untrusted_external_content", *flags],
        message=message,
    )


def preview_public_inspiration(
    raw_url: str,
    *,
    client: httpx.Client | None = None,
    resolver=assert_public_dns,
    fetch_enabled: bool = True,
) -> InspirationPreviewResponse:
    current_url = normalize_public_url(raw_url)
    if not fetch_enabled:
        return _manual_preview(
            current_url,
            "服务器已关闭公开页面预览；链接已保留，请手动填写标题和摘要。",
            "fetch_disabled",
        )

    owns_client = client is None
    active_client = client or httpx.Client(
        timeout=FETCH_TIMEOUT,
        follow_redirects=False,
        trust_env=False,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Journey-Inspiration-Preview/1.0",
        },
    )
    try:
        for redirect_count in range(MAX_REDIRECTS + 1):
            parsed = urlsplit(current_url)
            resolver(parsed.hostname or "")
            active_client.cookies.clear()
            try:
                with active_client.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location or redirect_count >= MAX_REDIRECTS:
                            return _manual_preview(
                                current_url,
                                "公开页面重定向过多；链接已保留，请手动填写。",
                                "redirect_blocked",
                            )
                        current_url = normalize_public_url(urljoin(current_url, location))
                        continue
                    if response.status_code != 200:
                        return _manual_preview(
                            current_url,
                            "公开页面当前不可读取；不会绕过登录或访问限制，请手动填写。",
                            f"http_{response.status_code}",
                        )
                    content_type = response.headers.get("content-type", "").lower()
                    if (
                        "text/html" not in content_type
                        and "application/xhtml+xml" not in content_type
                    ):
                        return _manual_preview(
                            current_url,
                            "链接不是可预览的公开网页；请手动填写。",
                            "unsupported_content_type",
                        )
                    declared_length = response.headers.get("content-length")
                    try:
                        declared_bytes = int(declared_length) if declared_length else None
                    except ValueError:
                        declared_bytes = None
                    if declared_bytes is not None and declared_bytes > MAX_RESPONSE_BYTES:
                        return _manual_preview(
                            current_url,
                            "页面超过预览大小限制；不会继续下载，请手动填写。",
                            "response_too_large",
                        )
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > MAX_RESPONSE_BYTES:
                            return _manual_preview(
                                current_url,
                                "页面超过预览大小限制；不会继续下载，请手动填写。",
                                "response_too_large",
                            )
                    charset = response.encoding or "utf-8"
                    try:
                        document = bytes(content).decode(charset, errors="replace")
                    except LookupError:
                        document = bytes(content).decode("utf-8", errors="replace")
            except httpx.HTTPError:
                return _manual_preview(
                    current_url,
                    "公开页面请求超时或不可达；链接已保留，请手动填写。",
                    "fetch_failed",
                )

            parser = _MetadataParser()
            parser.feed(document)
            title = _clean_text(parser.meta.get("og:title") or " ".join(parser.title_parts), 160)
            summary = _clean_text(
                parser.meta.get("og:description") or parser.meta.get("description"), 500
            )
            combined = f"{title or ''}\n{summary or ''}".lower()
            if any(marker in combined for marker in SUSPICIOUS_INSTRUCTIONS):
                return _manual_preview(
                    current_url,
                    "页面元数据包含疑似指令内容；未采纳，请手动填写。",
                    "prompt_injection_suspected",
                )
            if not title:
                return _manual_preview(
                    current_url,
                    "公开页面未提供可用标题；链接已保留，请手动填写。",
                    "metadata_missing",
                )
            return InspirationPreviewResponse(
                status="preview",
                source_url=current_url,
                title=title,
                summary=summary,
                source_checked_at=datetime.now(UTC),
                safety_flags=["untrusted_external_content", "inspiration_only"],
                message="仅提取公开页标题和短摘要；请确认后保存为生活灵感。",
            )
        return _manual_preview(current_url, "无法完成公开页面预览，请手动填写。")
    finally:
        if owns_client:
            active_client.close()


def create_inspiration(
    db: Session,
    user: User,
    payload: InspirationCreateRequest,
    request_id: str,
) -> LifeInspiration:
    source_url = normalize_public_url(payload.source_url)
    record = LifeInspiration(
        user_id=user.id,
        source_url=source_url,
        source_name="小红书",
        title=payload.title,
        summary=payload.summary,
        tags=payload.tags,
        evidence_level="inspiration_only",
        source_checked_at=payload.source_checked_at,
    )
    db.add(record)
    try:
        db.flush()
        add_audit(
            db,
            user_id=user.id,
            action="inspiration.created",
            resource_type="life_inspiration",
            resource_id=record.id,
            request_id=request_id,
            event_data={"source_name": "小红书", "evidence_level": "inspiration_only"},
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise APIError(
            status_code=409,
            code="inspiration_already_saved",
            message="This shared link is already saved",
        ) from error
    db.refresh(record)
    return record


def list_inspirations(
    db: Session, user: User, limit: int, offset: int
) -> Page[InspirationResponse]:
    base = select(LifeInspiration).where(LifeInspiration.user_id == user.id)
    items = list(
        db.scalars(
            base.order_by(LifeInspiration.created_at.desc(), LifeInspiration.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    total = int(
        db.scalar(
            select(func.count())
            .select_from(LifeInspiration)
            .where(LifeInspiration.user_id == user.id)
        )
        or 0
    )
    return Page(
        items=[InspirationResponse.model_validate(item) for item in items],
        meta=PageMeta(limit=limit, offset=offset, total=total),
    )


def delete_inspiration(
    db: Session,
    user: User,
    inspiration_id: uuid.UUID,
    request_id: str,
) -> None:
    record = db.scalar(
        select(LifeInspiration).where(
            LifeInspiration.id == inspiration_id,
            LifeInspiration.user_id == user.id,
        )
    )
    if record is None:
        raise APIError(
            status_code=404,
            code="inspiration_not_found",
            message="Life inspiration was not found",
        )
    db.delete(record)
    add_audit(
        db,
        user_id=user.id,
        action="inspiration.deleted",
        resource_type="life_inspiration",
        resource_id=inspiration_id,
        request_id=request_id,
    )
    db.commit()
