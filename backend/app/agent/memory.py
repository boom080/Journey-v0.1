import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.models.agent import AgentRun, AgentThread
from app.models.user import User
from app.schemas.agent import AgentCandidate

THREAD_MEMORY_VERSION = "journey-thread-memory-1"
MAX_THREAD_MEMORY_ITEMS = 8


def resolve_thread(
    db: Session,
    user: User,
    thread_id: uuid.UUID | None,
) -> AgentThread:
    if thread_id is None:
        thread = AgentThread(user_id=user.id, status="active", memory=[])
        db.add(thread)
        db.flush()
        return thread
    thread = db.scalar(
        select(AgentThread).where(
            AgentThread.id == thread_id,
            AgentThread.user_id == user.id,
            AgentThread.status == "active",
        )
    )
    if thread is None:
        raise APIError(
            status_code=404, code="agent_thread_not_found", message="Agent thread not found"
        )
    return thread


def memory_context(thread: AgentThread) -> list[dict]:
    return list(thread.memory[-MAX_THREAD_MEMORY_ITEMS:])


def remember_run(
    thread: AgentThread,
    run: AgentRun,
    *,
    candidates: list[AgentCandidate],
    answer_present: bool,
) -> None:
    existing = next(
        (item for item in thread.memory if item.get("run_id") == str(run.id)),
        None,
    )
    item = {
        "run_id": str(run.id),
        "intents": list(run.intents),
        "status": run.status,
        "candidate_kinds": [candidate.kind for candidate in candidates],
        "confirmed_kinds": list(existing.get("confirmed_kinds", [])) if existing else [],
        "answer_present": answer_present,
    }
    thread.memory = [
        *[entry for entry in thread.memory if entry.get("run_id") != str(run.id)],
        item,
    ][-MAX_THREAD_MEMORY_ITEMS:]
    thread.memory_version = THREAD_MEMORY_VERSION
    thread.updated_at = datetime.now(UTC)


def remember_confirmation(db: Session, run: AgentRun, kind: str) -> None:
    if run.thread_id is None:
        return
    thread = db.scalar(select(AgentThread).where(AgentThread.id == run.thread_id))
    if thread is None:
        return
    updated: list[dict] = []
    for item in thread.memory:
        copy = dict(item)
        if copy.get("run_id") == str(run.id):
            confirmed = list(copy.get("confirmed_kinds", []))
            if kind not in confirmed:
                confirmed.append(kind)
            copy["confirmed_kinds"] = confirmed
        updated.append(copy)
    thread.memory = updated[-MAX_THREAD_MEMORY_ITEMS:]
    thread.updated_at = datetime.now(UTC)
