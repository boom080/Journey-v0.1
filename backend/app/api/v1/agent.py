import uuid

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.agent import (
    AgentConfirmationRequest,
    AgentConfirmationResponse,
    AgentRunRequest,
    AgentRunResponse,
    AgentRunTrace,
    AgentSummaryResponse,
)
from app.schemas.agent_privacy import AgentConsentRequest, AgentDataDeletion, AgentPrivacyStatus
from app.services.agent import confirm_candidate, get_run_trace, resume_agent_run, run_agent
from app.services.agent_privacy import delete_agent_data, privacy_status, update_consent
from app.services.agent_summary import generate_summary

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/summaries/7-day", response_model=AgentSummaryResponse)
def create_seven_day_summary(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return generate_summary(
        db,
        user,
        period_days=7,
        request_id=request.state.request_id,
    )


@router.post("/summaries/30-day", response_model=AgentSummaryResponse)
def create_thirty_day_summary(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return generate_summary(
        db,
        user,
        period_days=30,
        request_id=request.state.request_id,
    )


@router.get("/privacy", response_model=AgentPrivacyStatus)
def read_privacy(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return privacy_status(db, user.id)


@router.put("/privacy/consent", response_model=AgentPrivacyStatus)
def write_consent(
    payload: AgentConsentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_consent(db, user.id, granted=payload.granted, version=payload.policy_version)


@router.delete("/privacy/data", response_model=AgentDataDeletion)
def erase_agent_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return delete_agent_data(db, user.id)


@router.post("/runs", response_model=AgentRunResponse)
def create_run(
    payload: AgentRunRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return run_agent(
        db,
        user,
        message=payload.message,
        thread_id=payload.thread_id,
        request_id=request.state.request_id,
    )


@router.get("/runs/{run_id}", response_model=AgentRunTrace)
def read_run_trace(
    run_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_run_trace(db, user, run_id)


@router.post("/runs/{run_id}/resume", response_model=AgentRunResponse)
def resume_run(
    run_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return resume_agent_run(db, user, run_id=run_id)


@router.post(
    "/confirmations/{candidate_id}",
    response_model=AgentConfirmationResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm(
    candidate_id: uuid.UUID,
    payload: AgentConfirmationRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=128),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return confirm_candidate(
        db,
        user,
        candidate_id=candidate_id,
        payload=payload,
        request_id=request.state.request_id,
        path=request.url.path,
        idempotency_key=idempotency_key,
    )
