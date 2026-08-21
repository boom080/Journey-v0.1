import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.records import ActivityRecordCreate, FoodRecordCreate, WeightRecordCreate

AgentIntent = Literal[
    "food",
    "activity",
    "weight",
    "profile",
    "history",
    "knowledge",
    "recommendation",
    "weekly_summary",
    "clarify",
]

AgentToolName = Literal[
    "context.load",
    "profile.read",
    "journey.read",
    "food.parse_candidate",
    "activity.parse_candidate",
    "weight.parse_candidate",
    "knowledge.answer",
    "knowledge.retrieve",
    "recommendation.generate",
    "weekly_summary.generate",
    "knowledge.safe_summary",
    "recommendation.rules_fallback",
]

AgentVerifierDecision = Literal[
    "done",
    "wait_for_user",
    "replan",
    "clarify",
    "fallback",
    "stop",
]

AgentSpecialist = Literal[
    "orchestrator",
    "record_agent",
    "health_knowledge_agent",
    "journey_summary_agent",
]


class AgentRunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    thread_id: uuid.UUID | None = None


class IntentItem(BaseModel):
    intent: AgentIntent
    confidence: float = Field(ge=0, le=1)
    segment: str = Field(max_length=500)


class IntentPlan(BaseModel):
    intents: list[IntentItem] = Field(min_length=1, max_length=8)
    needs_clarification: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)


class AgentPlanStep(BaseModel):
    id: str = Field(pattern=r"^(?:step-[1-6]|recovery-[1-2])$")
    tool: AgentToolName
    reason: str = Field(min_length=1, max_length=240)
    segment: str | None = Field(default=None, max_length=500)
    depends_on: list[str] = Field(default_factory=list, max_length=5)
    requires_confirmation: bool = False
    specialist: AgentSpecialist | None = None


class AgentPlan(BaseModel):
    schema_version: Literal["3"] = "3"
    goal: str = Field(min_length=1, max_length=500)
    steps: list[AgentPlanStep] = Field(min_length=1, max_length=6)
    needs_clarification: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)


class AgentPlanStepResult(BaseModel):
    step_id: str
    tool: AgentToolName
    status: Literal["completed", "failed", "skipped", "awaiting_confirmation"]
    message: str = Field(max_length=500)
    error_code: str | None = Field(default=None, max_length=80)
    specialist: AgentSpecialist = "orchestrator"
    duration_ms: int = Field(default=0, ge=0)


class AgentVerification(BaseModel):
    passed: bool
    completed_steps: int = Field(ge=0, le=6)
    failed_steps: int = Field(ge=0, le=6)
    skipped_steps: int = Field(ge=0, le=6)
    replan_count: int = Field(ge=0, le=2)
    reason: str = Field(max_length=500)
    decision: AgentVerifierDecision = "done"
    waiting_for_user: bool = False
    pending_confirmations: int = Field(default=0, ge=0, le=6)


class AgentObservation(BaseModel):
    step_id: str = Field(pattern=r"^(?:step-[1-6]|recovery-[1-2])$")
    tool: AgentToolName
    status: Literal["completed", "failed", "skipped", "awaiting_confirmation"]
    error_type: str | None = Field(default=None, max_length=80)
    recoverable: bool = False
    output_summary: dict[str, Any] = Field(default_factory=dict)
    allowed_alternatives: list[AgentToolName] = Field(default_factory=list, max_length=3)
    specialist: AgentSpecialist = "orchestrator"


class AgentRecoveryDecision(BaseModel):
    action: Literal["use_alternative", "stop"]
    tool: AgentToolName | None = None
    reason: str = Field(min_length=1, max_length=240)


class AgentConfirmationProgress(BaseModel):
    total: int = Field(ge=0, le=6)
    confirmed: int = Field(ge=0, le=6)
    pending: int = Field(ge=0, le=6)
    resume_available: bool = False


class FoodParsed(BaseModel):
    meal_type: Literal["breakfast", "lunch", "dinner", "snack", "other"]
    name: str = Field(min_length=1, max_length=120)
    energy_kcal: float = Field(ge=0, le=20000)
    portion_amount: float | None = Field(default=None, gt=0, le=100000)
    portion_unit: str | None = Field(default=None, max_length=30)


class ActivityParsed(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    duration_minutes: int = Field(gt=0, le=1440)
    intensity: Literal["low", "moderate", "high"]
    energy_kcal: float = Field(ge=0, le=20000)


class WeightParsed(BaseModel):
    weight_kg: float = Field(ge=25, le=400)


class AgentEvent(BaseModel):
    schema_version: Literal["1"] = "1"
    sequence: int = Field(ge=0)
    type: Literal[
        "status",
        "tool",
        "candidate",
        "knowledge",
        "observation",
        "verification",
        "error",
        "complete",
    ]
    message: str = Field(max_length=500)
    data: dict[str, Any] = Field(default_factory=dict)


class AgentCitation(BaseModel):
    chunk_id: str
    document_id: str
    source_slug: str
    title: str
    source_url: str
    version: str
    region: str
    score: float
    excerpt: str = Field(max_length=500)


class FoodAgentCandidate(BaseModel):
    kind: Literal["food"]
    candidate_id: uuid.UUID
    confirmation_token: str
    payload: FoodRecordCreate
    explanation: str


class ActivityAgentCandidate(BaseModel):
    kind: Literal["activity"]
    candidate_id: uuid.UUID
    confirmation_token: str
    payload: ActivityRecordCreate
    explanation: str


class WeightAgentCandidate(BaseModel):
    kind: Literal["weight"]
    candidate_id: uuid.UUID
    confirmation_token: str
    payload: WeightRecordCreate
    explanation: str


AgentCandidate = FoodAgentCandidate | ActivityAgentCandidate | WeightAgentCandidate


class AgentUsage(BaseModel):
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    retries: int = 0
    latency_ms: int = 0
    estimated_cost_usd: float = 0


class AgentRunResponse(BaseModel):
    run_id: uuid.UUID
    thread_id: uuid.UUID | None = None
    status: Literal["completed", "degraded", "clarification_required", "waiting_for_user"]
    intents: list[IntentItem]
    plan: AgentPlan | None = None
    step_results: list[AgentPlanStepResult] = Field(default_factory=list)
    verification: AgentVerification | None = None
    observations: list[AgentObservation] = Field(default_factory=list)
    confirmation_progress: AgentConfirmationProgress | None = None
    resumable: bool = False
    events: list[AgentEvent]
    candidates: list[AgentCandidate] = Field(default_factory=list)
    answer: str | None = None
    citations: list[AgentCitation] = Field(default_factory=list)
    fallback_used: bool = False
    safety_notice: str
    usage: AgentUsage
    selected_agents: list[AgentSpecialist] = Field(default_factory=list, max_length=4)


class AgentConfirmationRequest(BaseModel):
    confirmation_token: str = Field(min_length=20, max_length=2000)
    kind: Literal["food", "activity", "weight"]
    payload: FoodRecordCreate | ActivityRecordCreate | WeightRecordCreate


class AgentConfirmationResponse(BaseModel):
    candidate_id: uuid.UUID
    kind: Literal["food", "activity", "weight"]
    record: dict[str, Any]
    replayed: bool = False
    run_id: uuid.UUID | None = None
    run_status: str | None = None
    confirmation_progress: AgentConfirmationProgress | None = None
    resume_available: bool = False


class AgentToolTrace(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tool_name: str
    status: str
    input_summary: dict[str, Any]
    output_summary: dict[str, Any]
    latency_ms: int
    error_code: str | None
    created_at: datetime
    specialist: AgentSpecialist = "orchestrator"


class AgentRunTrace(BaseModel):
    run_id: uuid.UUID
    thread_id: uuid.UUID | None = None
    status: str
    intents: list[str]
    plan: AgentPlan | None = None
    verification: AgentVerification | None = None
    observations: list[AgentObservation] = Field(default_factory=list)
    replan_count: int = 0
    resume_count: int = 0
    checkpoint_status: Literal["none", "waiting", "ready", "expired", "consumed"] = "none"
    provider: str
    model: str
    prompt_version: str
    schema_version: str
    knowledge_version: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    retries: int
    estimated_cost_usd: float
    fallback_used: bool
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None
    tools: list[AgentToolTrace]
    selected_agents: list[AgentSpecialist] = Field(default_factory=list, max_length=4)
    confirmation_progress: AgentConfirmationProgress | None = None


class RecommendationGenerated(BaseModel):
    summary: str = Field(min_length=1, max_length=1200)
    cited_chunk_ids: list[str] = Field(default_factory=list, max_length=5)


class WeeklySummaryGenerated(BaseModel):
    summary: str = Field(min_length=1, max_length=1500)
    cited_chunk_ids: list[str] = Field(default_factory=list, max_length=5)


class KnowledgeGenerated(BaseModel):
    answer: str = Field(min_length=1, max_length=1200)
    cited_chunk_ids: list[str] = Field(default_factory=list, max_length=5)
