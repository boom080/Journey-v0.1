"""Server-side authorization and lifecycle for text Agent data.

The User row is the transaction mutex. Runs, consent changes, confirmations and
deletion take this lock in the same order. A successful revocation/deletion thus
cannot race a previously authorized run back into the database.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.core.provider_review import review_is_current
from app.core.settings import Settings, get_settings
from app.models.agent import AgentRun, AgentSummaryCache, AgentThread
from app.models.agent_privacy import AgentConsent, AgentDeletedCost
from app.models.audit import AuditEvent
from app.models.idempotency import IdempotencyKey
from app.models.user import User
from app.schemas.agent_privacy import AgentDataDeletion, AgentPrivacyStatus

DATA_SENT = [
    "本次输入中完成任务所需的文字（可能含健康信息；常见联系方式及凭据会被过滤）",
    "建议/周总结所需的目标、能量与记录计数聚合，不发送姓名、账号、生日或逐条历史记录",
    "最近最多 8 次会话的任务类型与确认状态（不含 run/user ID）及受控公开知识片段",
]
DELETION_NOTICE = (
    "删除会撤回授权并清除 Journey 活跃数据库中的 Agent 运行、工具 Trace、候选、"
    "检查点、线程记忆与确认回放缓存，不删除你已确认保存的健康记录。"
    "已发送给供应商的数据及运维备份不在此 API 删除范围内；本项目不声称供应商已删除。"
    "仓库恢复工具只恢复到隔离数据库，并统一丢弃旧 Agent 状态和授权，保留已确认健康记录；"
    "禁止绕过清理直接开放旧备份。历史及第三方备份仍需运维单独管理。"
)


def disclosure_version(settings: Settings) -> str:
    contract = {
        "version": "journey-text-privacy-1",
        "provider": settings.agent_provider,
        "endpoint": settings.agent_api_base_url,
        "model": settings.agent_default_model,
        "models": settings.agent_model_map,
        "policy_url": settings.agent_provider_policy_url,
        "retention_notice": settings.agent_provider_retention_notice,
        "local_retention": settings.agent_data_retention_days,
        "provider_review_required": settings.agent_provider_review_required,
        "data": DATA_SENT,
        "deletion": DELETION_NOTICE,
    }
    return hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()


def policy_version(settings: Settings) -> str:
    return hashlib.sha256(
        (disclosure_version(settings) + settings.agent_provider_review_json).encode()
    ).hexdigest()


def provider_review_ready(settings: Settings) -> bool:
    if settings.environment == "local" and not settings.agent_provider_review_required:
        return True
    return review_is_current(settings.agent_provider_review_json, disclosure_version(settings))


def require_provider_review(settings: Settings) -> None:
    if not provider_review_ready(settings):
        raise APIError(
            status_code=503,
            code="agent_provider_review_required",
            message="外部 AI 部署审核未完成、已过期或与当前配置不一致，暂不可用",
        )


def lock_user(db: Session, user_id: uuid.UUID) -> None:
    if db.scalar(select(User.id).where(User.id == user_id).with_for_update()) is None:
        raise APIError(status_code=401, code="unauthorized", message="请重新登录")


def _consent(db: Session, user_id: uuid.UUID) -> AgentConsent | None:
    return db.scalar(
        select(AgentConsent)
        .where(AgentConsent.user_id == user_id)
        .execution_options(populate_existing=True)
    )


def require_external_consent(db: Session, user_id: uuid.UUID | None, settings: Settings) -> None:
    if settings.agent_provider == "mock":
        return
    if not settings.agent_external_enabled:
        raise APIError(
            status_code=503,
            code="agent_external_disabled",
            message="外部 AI 尚未完成部署隐私配置，暂不可用",
        )
    require_provider_review(settings)
    if user_id is None:
        raise APIError(
            status_code=403, code="consent_required", message="请先阅读并同意外部 AI 数据使用说明"
        )
    lock_user(db, user_id)
    consent = _consent(db, user_id)
    if consent is None or consent.granted_at is None:
        raise APIError(
            status_code=403, code="consent_required", message="请先阅读并同意外部 AI 数据使用说明"
        )
    if consent.policy_version != policy_version(settings):
        raise APIError(
            status_code=403,
            code="consent_outdated",
            message="供应商或数据使用说明已变更，请重新确认",
        )


def privacy_status(
    db: Session, user_id: uuid.UUID, settings: Settings | None = None
) -> AgentPrivacyStatus:
    settings = settings or get_settings()
    consent = _consent(db, user_id)
    version = policy_version(settings)
    granted = bool(consent and consent.granted_at and consent.policy_version == version)
    return AgentPrivacyStatus(
        provider=settings.agent_provider,
        external=settings.agent_provider != "mock",
        enabled=settings.agent_provider == "mock"
        or (settings.agent_external_enabled and provider_review_ready(settings)),
        policy_version=version,
        consent_granted=granted,
        granted_at=consent.granted_at if granted else None,
        retention_days=settings.agent_data_retention_days,
        notice=(
            (
                "当前为仅限本机的个人使用模式，不要求企业级供应商审核证明。"
                "文字仍会发送给外部 AI；拒绝或撤回不影响手动记录。"
            )
            if settings.environment == "local" and not settings.agent_provider_review_required
            else (
                "外部 AI 为可选功能。拒绝或撤回不影响手动记录、同步与离线常识查询。"
                "请勿在输入中包含姓名、联系方式、证件号或密钥；"
                "过滤器不能保证识别所有自由文本敏感信息。"
            )
        ),
        data_sent=DATA_SENT,
        provider_policy_url=settings.agent_provider_policy_url or None,
        provider_retention_notice=settings.agent_provider_retention_notice
        or "未完成供应商保留/删除政策核验，外部发送默认关闭。",
        deletion_notice=DELETION_NOTICE,
    )


def update_consent(
    db: Session, user_id: uuid.UUID, *, granted: bool, version: str
) -> AgentPrivacyStatus:
    settings = get_settings()
    lock_user(db, user_id)
    if granted:
        if settings.agent_provider == "mock" or not settings.agent_external_enabled:
            raise APIError(
                status_code=409,
                code="agent_external_disabled",
                message="当前没有可授权的外部 AI 服务",
            )
        require_provider_review(settings)
        if version != policy_version(settings):
            raise APIError(
                status_code=409, code="consent_outdated", message="说明已更新，请刷新后重新确认"
            )
    consent = _consent(db, user_id)
    if consent is None:
        consent = AgentConsent(user_id=user_id, policy_version=policy_version(settings))
        db.add(consent)
    consent.policy_version = policy_version(settings)
    consent.granted_at = datetime.now(UTC) if granted else None
    db.commit()
    return privacy_status(db, user_id, settings)


def purge_user_data(
    db: Session, user_id: uuid.UUID, *, cutoff: datetime | None = None
) -> tuple[int, int]:
    """Caller holds the user lock. FK cascades delete tools and confirmation tokens."""
    query = select(AgentRun).where(AgentRun.user_id == user_id)
    if cutoff is not None:
        query = query.where(AgentRun.created_at < cutoff)
    runs = list(db.scalars(query))
    run_ids = {str(run.id) for run in runs}
    today = datetime.now(UTC).date()
    # Deleting private history must not reset the global paid-model daily budget.
    deleted_cost = sum(
        float(run.estimated_cost_usd) for run in runs if run.created_at.date() == today
    )
    if deleted_cost:
        stmt = insert(AgentDeletedCost).values(day=today, cost_usd=deleted_cost)
        db.execute(
            stmt.on_conflict_do_update(
                index_elements=[AgentDeletedCost.day],
                set_={"cost_usd": AgentDeletedCost.cost_usd + stmt.excluded.cost_usd},
            )
        )
    if runs:
        db.execute(delete(AgentRun).where(AgentRun.id.in_([run.id for run in runs])))
    summary_cache_query = delete(AgentSummaryCache).where(AgentSummaryCache.user_id == user_id)
    if cutoff is not None:
        summary_cache_query = summary_cache_query.where(AgentSummaryCache.updated_at < cutoff)
    db.execute(summary_cache_query)
    threads = list(db.scalars(select(AgentThread).where(AgentThread.user_id == user_id)))
    deleted_threads = 0
    for thread in threads:
        thread.memory = [entry for entry in thread.memory if entry.get("run_id") not in run_ids]
        if cutoff is None or thread.updated_at < cutoff:
            db.delete(thread)
            deleted_threads += 1
    for replay in db.scalars(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == user_id, IdempotencyKey.path.like("/api/v1/agent/%")
        )
    ):
        if (
            cutoff is None
            or replay.created_at < cutoff
            or replay.expires_at <= datetime.now(UTC)
            or replay.response_body.get("run_id") in run_ids
        ):
            db.delete(replay)
    audit_query = delete(AuditEvent).where(
        AuditEvent.user_id == user_id,
        AuditEvent.resource_type.in_(["agent", "agent_run", "agent_thread", "agent_consent"]),
    )
    if cutoff is not None:
        audit_query = audit_query.where(AuditEvent.created_at < cutoff)
    db.execute(audit_query)
    db.flush()
    return len(runs), deleted_threads


def prepare_agent_access(db: Session, user_id: uuid.UUID) -> None:
    lock_user(db, user_id)
    cutoff = datetime.now(UTC) - timedelta(days=get_settings().agent_data_retention_days)
    purge_user_data(db, user_id, cutoff=cutoff)


def delete_agent_data(db: Session, user_id: uuid.UUID) -> AgentDataDeletion:
    lock_user(db, user_id)
    consent = _consent(db, user_id)
    if consent is not None:
        db.delete(consent)
    runs, threads = purge_user_data(db, user_id)
    db.commit()
    return AgentDataDeletion(deleted_runs=runs, deleted_threads=threads, message=DELETION_NOTICE)


def purge_expired_agent_data() -> None:
    from app.core.database import SessionLocal

    cutoff = datetime.now(UTC) - timedelta(days=get_settings().agent_data_retention_days)
    with SessionLocal() as db:
        users = set(db.scalars(select(AgentRun.user_id).where(AgentRun.created_at < cutoff)))
        users.update(db.scalars(select(AgentThread.user_id).where(AgentThread.updated_at < cutoff)))
        users.update(
            db.scalars(
                select(AgentSummaryCache.user_id).where(AgentSummaryCache.updated_at < cutoff)
            )
        )
        users.update(
            db.scalars(
                select(IdempotencyKey.user_id).where(
                    IdempotencyKey.path.like("/api/v1/agent/%"),
                    IdempotencyKey.expires_at < datetime.now(UTC),
                )
            )
        )
    for user_id in users:
        with SessionLocal() as db:
            lock_user(db, user_id)
            purge_user_data(db, user_id, cutoff=cutoff)
            db.commit()
    with SessionLocal() as db:
        db.execute(delete(AgentDeletedCost).where(AgentDeletedCost.day < datetime.now(UTC).date()))
        db.commit()
