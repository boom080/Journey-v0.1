export type ApiHealthStatus = 'ok' | 'unavailable';

export type ApiHealthResponse = {
  status: ApiHealthStatus;
  service: 'journey-api';
  environment: string;
  database?: 'ok' | 'unavailable';
  rag?: 'ok' | 'empty' | 'unavailable';
  agent_mode?: 'MOCK' | 'REAL';
  agent_provider?: string;
  agent_model?: string;
};

export type UUID = string;
export type ISODate = string;
export type ISODateTime = string;

export type ApiErrorResponse = {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
  request_id: string;
};

export type IdentityKind = 'email' | 'username' | 'phone';
export type GoalKind = 'lose_fat' | 'gain_muscle' | 'maintain';
export type RecordSource = 'manual' | 'agent' | 'image' | 'import';

export type Identity = {
  kind: IdentityKind;
  display_value: string;
  is_verified: boolean;
};

export type JourneyUser = {
  id: UUID;
  status: 'active' | 'disabled';
  identities: Identity[];
  created_at: ISODateTime;
};

export type TokenPair = {
  token_type: 'bearer';
  access_token: string;
  access_expires_at: ISODateTime;
  refresh_token: string;
  refresh_expires_at: ISODateTime;
  user: JourneyUser;
};

export type JourneyProfile = {
  user_id: UUID;
  display_name: string;
  timezone: string;
  locale: string;
  sex: 'female' | 'male' | 'other' | 'undisclosed' | null;
  birth_date: ISODate | null;
  height_cm: number | null;
  preferred_unit: 'metric' | 'imperial';
  latest_weight_kg: number | null;
  version: number;
  updated_at: ISODateTime;
};

export type PageMeta = {
  limit: number;
  offset: number;
  total: number;
};

export type RegisterRequest = {
  email: string;
  username: string;
  password: string;
  display_name: string;
};

export type LoginRequest = { identifier: string; password: string };
export type RefreshRequest = { refresh_token: string };
export type MessageResponse = { message: string };

export type ProfileUpdateRequest = Partial<{
  display_name: string;
  timezone: string;
  locale: string;
  sex: JourneyProfile['sex'];
  birth_date: ISODate | null;
  height_cm: number | null;
  preferred_unit: JourneyProfile['preferred_unit'];
}>;

export type Goal = {
  id: UUID;
  kind: GoalKind;
  target_weight_kg: number | null;
  daily_energy_target_kcal: number | null;
  starts_on: ISODate;
  target_date: ISODate | null;
  is_active: boolean;
  version: number;
  updated_at: ISODateTime;
};

export type GoalUpsertRequest = {
  kind: GoalKind;
  target_weight_kg?: number | null;
  daily_energy_target_kcal?: number | null;
  starts_on?: ISODate;
  target_date?: ISODate | null;
};

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack' | 'other';
export type ActivityIntensity = 'low' | 'moderate' | 'high';

export type FoodRecordCreate = {
  recorded_at: ISODateTime;
  meal_type: MealType;
  name: string;
  energy_kcal: number;
  detail?: string | null;
  portion_amount?: number | null;
  portion_unit?: string | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  source?: RecordSource;
  source_ref?: string | null;
};

export type FoodRecord = FoodRecordCreate & {
  id: UUID;
  record_date: ISODate;
  source: RecordSource;
  version: number;
  created_at: ISODateTime;
  updated_at: ISODateTime;
};

export type ActivityRecordCreate = {
  recorded_at: ISODateTime;
  name: string;
  activity_type?: string | null;
  duration_minutes: number;
  intensity: ActivityIntensity;
  energy_kcal: number;
  note?: string | null;
  source?: RecordSource;
  source_ref?: string | null;
};

export type ActivityRecord = ActivityRecordCreate & {
  id: UUID;
  record_date: ISODate;
  source: RecordSource;
  version: number;
  created_at: ISODateTime;
  updated_at: ISODateTime;
};

export type WeightRecordCreate = {
  measured_at: ISODateTime;
  weight_kg: number;
  note?: string | null;
  source?: RecordSource;
};

export type WeightRecord = WeightRecordCreate & {
  id: UUID;
  record_date: ISODate;
  source: RecordSource;
  version: number;
  created_at: ISODateTime;
  updated_at: ISODateTime;
};

export type Page<T> = { items: T[]; meta: PageMeta };

export type InspirationPreviewRequest = { source_url: string };

export type InspirationPreview = {
  status: 'preview' | 'manual_required';
  source_url: string;
  source_name: '小红书';
  title: string | null;
  summary: string | null;
  source_checked_at: ISODateTime;
  safety_flags: string[];
  message: string;
};

export type InspirationCreate = {
  source_url: string;
  title: string;
  summary?: string | null;
  tags: string[];
  source_checked_at: ISODateTime;
  confirmed: true;
};

export type LifeInspiration = {
  id: UUID;
  source_url: string;
  source_name: string;
  title: string;
  summary: string | null;
  tags: string[];
  evidence_level: 'inspiration_only';
  source_checked_at: ISODateTime;
  created_at: ISODateTime;
  updated_at: ISODateTime;
};

export type HomeToday = {
  date: ISODate;
  timezone: string;
  intake_kcal: number;
  activity_kcal: number;
  net_kcal: number;
  resting_energy: {
    status: 'available' | 'missing_profile' | 'unsupported_profile';
    kcal_per_day: number | null;
    formula: 'mifflin-st-jeor-1990';
    age_years: number | null;
    missing_fields: string[];
    note: string;
  };
  estimated_energy_balance_kcal: number | null;
  counts: { food: number; activity: number; weight: number };
  latest_weight_kg: number | null;
  active_goal: Goal | null;
};

export type JourneyDay = {
  date: ISODate;
  intake_kcal: number;
  activity_kcal: number;
  net_kcal: number;
  food_records: FoodRecord[];
  activity_records: ActivityRecord[];
  weight_records: WeightRecord[];
};

export type JourneyResponse = {
  items: JourneyDay[];
  next_cursor: ISODate | null;
  has_more: boolean;
};

export type ManualRecordKind = 'food' | 'activity' | 'weight';
export type ManualRecordPayload = FoodRecordCreate | ActivityRecordCreate | WeightRecordCreate;

export type PendingMutation = {
  id: string;
  ownerUserId: UUID;
  kind: ManualRecordKind;
  idempotencyKey: string;
  payload: ManualRecordPayload;
  createdAt: ISODateTime;
  attempts: number;
};

export type AgentIntent =
  | 'food'
  | 'activity'
  | 'weight'
  | 'profile'
  | 'history'
  | 'knowledge'
  | 'recommendation'
  | 'weekly_summary'
  | 'clarify';

export type AgentIntentItem = {
  intent: AgentIntent;
  confidence: number;
  segment: string;
};

export type AgentToolName =
  | 'context.load'
  | 'profile.read'
  | 'journey.read'
  | 'food.parse_candidate'
  | 'activity.parse_candidate'
  | 'weight.parse_candidate'
  | 'knowledge.answer'
  | 'knowledge.retrieve'
  | 'recommendation.generate'
  | 'weekly_summary.generate'
  | 'knowledge.safe_summary'
  | 'recommendation.rules_fallback';

export type AgentSpecialist =
  | 'orchestrator'
  | 'record_agent'
  | 'health_knowledge_agent'
  | 'journey_summary_agent';

export type AgentPlanStep = {
  id: string;
  tool: AgentToolName;
  reason: string;
  segment: string | null;
  depends_on: string[];
  requires_confirmation: boolean;
  specialist: AgentSpecialist | null;
};

export type AgentPlan = {
  schema_version: '3';
  goal: string;
  steps: AgentPlanStep[];
  needs_clarification: boolean;
  clarification_question: string | null;
};

export type AgentPlanStepResult = {
  step_id: string;
  tool: AgentToolName;
  status: 'completed' | 'failed' | 'skipped' | 'awaiting_confirmation';
  message: string;
  error_code: string | null;
  specialist: AgentSpecialist;
  duration_ms: number;
};

export type AgentVerification = {
  passed: boolean;
  completed_steps: number;
  failed_steps: number;
  skipped_steps: number;
  replan_count: number;
  reason: string;
  decision: 'done' | 'wait_for_user' | 'replan' | 'clarify' | 'fallback' | 'stop';
  waiting_for_user: boolean;
  pending_confirmations: number;
};

export type AgentObservation = {
  step_id: string;
  tool: AgentToolName;
  status: AgentPlanStepResult['status'];
  error_type: string | null;
  recoverable: boolean;
  output_summary: Record<string, unknown>;
  allowed_alternatives: AgentToolName[];
  specialist: AgentSpecialist;
};

export type AgentConfirmationProgress = {
  total: number;
  confirmed: number;
  pending: number;
  resume_available: boolean;
};

export type AgentEvent = {
  schema_version: '1';
  sequence: number;
  type: 'status' | 'tool' | 'candidate' | 'knowledge' | 'observation' | 'verification' | 'error' | 'complete';
  message: string;
  data: Record<string, unknown>;
};

export type AgentCitation = {
  chunk_id: string;
  document_id: string;
  source_slug: string;
  title: string;
  source_url: string;
  version: string;
  region: string;
  score: number;
  excerpt: string;
};

type AgentCandidateBase = {
  candidate_id: UUID;
  confirmation_token: string;
  explanation: string;
};

export type AgentCandidate =
  | (AgentCandidateBase & { kind: 'food'; payload: FoodRecordCreate })
  | (AgentCandidateBase & { kind: 'activity'; payload: ActivityRecordCreate })
  | (AgentCandidateBase & { kind: 'weight'; payload: WeightRecordCreate });

export type AgentUsage = {
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  retries: number;
  latency_ms: number;
  estimated_cost_usd: number;
};

export type AgentRunResponse = {
  run_id: UUID;
  thread_id: UUID | null;
  status: 'completed' | 'degraded' | 'clarification_required' | 'waiting_for_user';
  intents: AgentIntentItem[];
  plan: AgentPlan | null;
  step_results: AgentPlanStepResult[];
  verification: AgentVerification | null;
  observations: AgentObservation[];
  confirmation_progress: AgentConfirmationProgress | null;
  resumable: boolean;
  events: AgentEvent[];
  candidates: AgentCandidate[];
  answer: string | null;
  citations: AgentCitation[];
  fallback_used: boolean;
  safety_notice: string;
  usage: AgentUsage;
  selected_agents: AgentSpecialist[];
};

export type AgentConfirmationRequest = {
  confirmation_token: string;
  kind: ManualRecordKind;
  payload: ManualRecordPayload;
};

export type AgentConfirmationResponse = {
  candidate_id: UUID;
  kind: ManualRecordKind;
  record: FoodRecord | ActivityRecord | WeightRecord;
  replayed: boolean;
  run_id: UUID | null;
  run_status: string | null;
  confirmation_progress: AgentConfirmationProgress | null;
  resume_available: boolean;
};

export type AgentRunTrace = {
  run_id: UUID;
  thread_id: UUID | null;
  status: 'completed' | 'degraded' | 'clarification_required' | 'waiting_for_user';
  checkpoint_status: 'none' | 'waiting' | 'ready' | 'expired' | 'consumed';
  confirmation_progress: AgentConfirmationProgress | null;
};

export type FoodImageScaleReferenceType =
  | 'none'
  | 'journey_card'
  | 'plate_diameter'
  | 'bowl_diameter';

export type FoodImageAnalyzeRequest = {
  image_base64: string;
  media_type: 'image/jpeg' | 'image/png' | 'image/webp';
  width: number;
  height: number;
  meal_type_hint: MealType;
  note?: string | null;
  scale_reference_type?: FoodImageScaleReferenceType;
  scale_reference_size_cm?: number | null;
  confirm_upload: true;
};

export type FoodImageItem = {
  name: string;
  canonical_name_en?: string | null;
  portion_amount: number | null;
  portion_unit: string | null;
  energy_kcal: number | null;
};

export type FoodImageEstimate = {
  is_food: boolean;
  name: string | null;
  canonical_name_en?: string | null;
  items: FoodImageItem[];
  meal_type: MealType;
  portion_amount: number | null;
  portion_unit: string | null;
  energy_kcal: number | null;
  energy_min_kcal: number | null;
  energy_max_kcal: number | null;
  confidence: 'low' | 'medium';
  assumptions: string[];
  scale_reference_used: boolean;
  needs_user_correction: true;
};

export type FoodImageAnalysisResponse = {
  analysis_id: UUID;
  status: 'candidate' | 'manual_required';
  candidate: Extract<AgentCandidate, { kind: 'food' }> | null;
  estimate: FoodImageEstimate | null;
  message: string;
  fallback_used: boolean;
  image_retained: false;
  usage: AgentUsage;
};

/**
 * Stage 5 reserves this transport-neutral event shape for the future Agent UI.
 * The Mock implementation only emits local candidates; no model SDK or Agent
 * backend is connected yet.
 */
export type AgentUiEvent =
  | { schemaVersion: '1'; type: 'status'; runId: string; message: string }
  | { schemaVersion: '1'; type: 'candidate'; runId: string; candidateId: string; intent: ManualRecordKind; payload: ManualRecordPayload }
  | { schemaVersion: '1'; type: 'knowledge'; runId: string; title: string; answer: string; sourceVersion: string }
  | { schemaVersion: '1'; type: 'error'; runId: string; code: string; message: string; retryable: boolean }
  | { schemaVersion: '1'; type: 'complete'; runId: string };
