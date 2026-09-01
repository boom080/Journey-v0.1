import type {
  AgentConfirmationRequest,
  AgentConfirmationResponse,
  AgentConsentRequest,
  AgentDataDeletion,
  AgentPrivacyStatus,
  AgentRunResponse,
  AgentRunTrace,
  ActivityRecord,
  ActivityRecordCreate,
  ApiErrorResponse,
  ApiHealthResponse,
  FoodRecord,
  FoodRecordCreate,
  FoodImageAnalysisResponse,
  FoodImageAnalyzeRequest,
  Goal,
  GoalUpsertRequest,
  HomeToday,
  InspirationCreate,
  InspirationPreview,
  InspirationPreviewRequest,
  JourneyProfile,
  JourneyResponse,
  LoginRequest,
  LifeInspiration,
  MessageResponse,
  Page,
  ProfileUpdateRequest,
  RefreshRequest,
  RegisterRequest,
  TokenPair,
  WeightRecord,
  WeightRecordCreate,
} from '@journey/contracts';

import { getApiBaseUrl } from '@/config/environment';
import { clearStoredSession, loadStoredSession, saveStoredSession } from '@/lib/session-storage';

export const REQUEST_TIMEOUT_MS = 10_000;
export const AGENT_REQUEST_TIMEOUT_MS = 120_000;
type SessionListener = (session: TokenPair | null) => void;
const sessionListeners = new Set<SessionListener>();
type AgentDataDeletedListener = () => void;
const agentDataDeletedListeners = new Set<AgentDataDeletedListener>();
let agentDataRevision = 0;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
    readonly details?: unknown,
  ) {
    super(message);
  }
}

export class ApiNetworkError extends Error {}

export function subscribeToSession(listener: SessionListener): () => void {
  sessionListeners.add(listener);
  return () => sessionListeners.delete(listener);
}

/**
 * Notify in-memory Agent consumers after the server confirms a data deletion.
 * This deliberately does not persist anything; it only lets mounted screens
 * discard their local run/thread/candidate state.
 */
export function subscribeToAgentDataDeleted(listener: AgentDataDeletedListener): () => void {
  agentDataDeletedListeners.add(listener);
  return () => agentDataDeletedListeners.delete(listener);
}

export function notifyAgentDataDeleted(): void {
  agentDataRevision += 1;
  agentDataDeletedListeners.forEach((listener) => listener());
}

/** Monotonic in-memory marker used to ignore Agent responses that finish after deletion. */
export function getAgentDataRevision(): number {
  return agentDataRevision;
}

async function setSession(session: TokenPair | null) {
  if (session) await saveStoredSession(session);
  else await clearStoredSession();
  sessionListeners.forEach((listener) => listener(session));
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const payload = (await response.json()) as ApiErrorResponse;
    return new ApiError(payload.error.message, payload.error.code, response.status, payload.error.details);
  } catch {
    return new ApiError(`请求失败（${response.status}）`, 'HTTP_ERROR', response.status);
  }
}

async function rawRequest<T>(
  path: string,
  init: RequestInit = {},
  options: { auth?: boolean; retryAuth?: boolean; timeoutMs?: number } = {},
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? REQUEST_TIMEOUT_MS);
  const session = options.auth === false ? null : await loadStoredSession();
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (session?.access_token) headers.set('Authorization', `Bearer ${session.access_token}`);

  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, { ...init, headers, signal: controller.signal });
    if (response.status === 401 && options.auth !== false && options.retryAuth !== false && session?.refresh_token) {
      const refreshed = await refreshSession({ refresh_token: session.refresh_token }).catch(() => null);
      if (refreshed) return rawRequest<T>(path, init, { ...options, retryAuth: false });
      await setSession(null);
    }
    if (!response.ok) throw await parseError(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiNetworkError('请求超时，请稍后重试');
    }
    throw new ApiNetworkError('网络不可用，请检查连接');
  } finally {
    clearTimeout(timeout);
  }
}

export async function login(payload: LoginRequest): Promise<TokenPair> {
  const session = await rawRequest<TokenPair>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, { auth: false });
  await setSession(session);
  return session;
}

export async function register(payload: RegisterRequest): Promise<TokenPair> {
  const session = await rawRequest<TokenPair>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, { auth: false });
  await setSession(session);
  return session;
}

export async function refreshSession(payload: RefreshRequest): Promise<TokenPair> {
  const session = await rawRequest<TokenPair>('/api/v1/auth/refresh', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, { auth: false });
  await setSession(session);
  return session;
}

export async function logout(): Promise<void> {
  const session = await loadStoredSession();
  if (session) {
    await rawRequest<MessageResponse>('/api/v1/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    }).catch(() => undefined);
  }
  await setSession(null);
}

export async function restoreSession(): Promise<TokenPair | null> {
  const session = await loadStoredSession();
  if (!session) return null;
  if (new Date(session.refresh_expires_at).getTime() <= Date.now()) {
    await setSession(null);
    return null;
  }
  if (new Date(session.access_expires_at).getTime() <= Date.now() + 30_000) {
    return refreshSession({ refresh_token: session.refresh_token }).catch(async () => {
      await setSession(null);
      return null;
    });
  }
  return session;
}

export const fetchProfile = () => rawRequest<JourneyProfile>('/api/v1/profile');
export const updateProfile = (payload: ProfileUpdateRequest, expectedVersion: number) =>
  rawRequest<JourneyProfile>('/api/v1/profile', {
    method: 'PATCH',
    headers: { 'If-Match-Version': String(expectedVersion) },
    body: JSON.stringify(payload),
  });
export const fetchGoal = () => rawRequest<Goal>('/api/v1/goals/current');
export const saveGoal = (payload: GoalUpsertRequest, expectedVersion: number) =>
  rawRequest<Goal>('/api/v1/goals/current', {
    method: 'PUT',
    headers: { 'If-Match-Version': String(expectedVersion) },
    body: JSON.stringify(payload),
  });
export const fetchHomeToday = () => rawRequest<HomeToday>('/api/v1/home/today');
export const fetchJourney = (limit = 7, cursor?: string, windowDays?: number) =>
  rawRequest<JourneyResponse>(`/api/v1/journey?limit=${limit}${cursor ? `&cursor=${cursor}` : ''}${windowDays ? `&window_days=${windowDays}` : ''}`);

const recordPath = { food: 'food-records', activity: 'activity-records', weight: 'weight-records' } as const;
export type RecordKind = keyof typeof recordPath;

export async function createRecord(
  kind: RecordKind,
  payload: FoodRecordCreate | ActivityRecordCreate | WeightRecordCreate,
  idempotencyKey: string,
): Promise<FoodRecord | ActivityRecord | WeightRecord> {
  return rawRequest(`/api/v1/${recordPath[kind]}`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(payload),
  });
}

export async function updateRecord(
  kind: RecordKind,
  id: string,
  payload: Record<string, unknown>,
  expectedVersion: number,
): Promise<FoodRecord | ActivityRecord | WeightRecord> {
  return rawRequest(`/api/v1/${recordPath[kind]}/${id}`, {
    method: 'PATCH',
    headers: { 'If-Match-Version': String(expectedVersion) },
    body: JSON.stringify(payload),
  });
}

export const deleteRecord = (kind: RecordKind, id: string, expectedVersion: number) =>
  rawRequest<void>(`/api/v1/${recordPath[kind]}/${id}`, {
    method: 'DELETE',
    headers: { 'If-Match-Version': String(expectedVersion) },
  });

export const listFoodRecords = () => rawRequest<Page<FoodRecord>>('/api/v1/food-records?limit=100');
export const listActivityRecords = () => rawRequest<Page<ActivityRecord>>('/api/v1/activity-records?limit=100');
export const listWeightRecords = () => rawRequest<Page<WeightRecord>>('/api/v1/weight-records?limit=100');

export const previewInspiration = (payload: InspirationPreviewRequest) =>
  rawRequest<InspirationPreview>('/api/v1/inspirations/preview', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const createInspiration = (payload: InspirationCreate) =>
  rawRequest<LifeInspiration>('/api/v1/inspirations', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const listInspirations = () =>
  rawRequest<Page<LifeInspiration>>('/api/v1/inspirations?limit=100');

export const deleteInspiration = (id: string) =>
  rawRequest<MessageResponse>(`/api/v1/inspirations/${id}`, { method: 'DELETE' });

export const runAgent = (message: string, threadId?: string) =>
  rawRequest<AgentRunResponse>('/api/v1/agent/runs', {
    method: 'POST',
    body: JSON.stringify({ message, thread_id: threadId }),
  }, { timeoutMs: AGENT_REQUEST_TIMEOUT_MS });

export const fetchAgentPrivacy = () =>
  rawRequest<AgentPrivacyStatus>('/api/v1/agent/privacy');

export const updateAgentConsent = (payload: AgentConsentRequest) =>
  rawRequest<AgentPrivacyStatus>('/api/v1/agent/privacy/consent', {
    method: 'PUT',
    body: JSON.stringify(payload),
  }, { timeoutMs: AGENT_REQUEST_TIMEOUT_MS });

export const deleteAgentData = () =>
  rawRequest<AgentDataDeletion>('/api/v1/agent/privacy/data', {
    method: 'DELETE',
  }, { timeoutMs: AGENT_REQUEST_TIMEOUT_MS });

const agentPrivacyErrorMessages: Record<string, string> = {
  agent_provider_review_required: '外部 AI 的部署审核尚未完成或已过期，消息未发送；请到“外部 AI 与数据”查看状态。',
  consent_required: '使用外部 AI 前需要先在“外部 AI 与数据”中明确授权；消息尚未发送。',
  consent_outdated: '外部 AI 的隐私政策已更新，请在“外部 AI 与数据”中重新确认后再试。',
  agent_external_disabled: '外部 AI 当前已关闭，消息不会发送；你可以在“外部 AI 与数据”查看当前状态。',
};

export function getAgentErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return agentPrivacyErrorMessages[error.code] ?? error.message;
  if (error instanceof ApiNetworkError) return `${error.message}；结果尚未确认，请刷新状态后重试。`;
  return 'Agent 暂时不可用，操作未确认完成，请刷新状态后重试。';
}

export const resumeAgentRun = (runId: string) =>
  rawRequest<AgentRunResponse>(`/api/v1/agent/runs/${runId}/resume`, {
    method: 'POST',
  }, { timeoutMs: AGENT_REQUEST_TIMEOUT_MS });

export const fetchAgentRunTrace = (runId: string) =>
  rawRequest<AgentRunTrace>(`/api/v1/agent/runs/${runId}`);

export const analyzeFoodImage = (payload: FoodImageAnalyzeRequest) =>
  rawRequest<FoodImageAnalysisResponse>('/api/v1/food-images/analyses', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const confirmAgentCandidate = (
  candidateId: string,
  payload: AgentConfirmationRequest,
  idempotencyKey: string,
) => rawRequest<AgentConfirmationResponse>(`/api/v1/agent/confirmations/${candidateId}`, {
  method: 'POST',
  headers: { 'Idempotency-Key': idempotencyKey },
  body: JSON.stringify(payload),
});

export async function fetchApiHealth(): Promise<ApiHealthResponse> {
  return rawRequest<ApiHealthResponse>('/health/live', {}, { auth: false });
}
