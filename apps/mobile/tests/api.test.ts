import type { TokenPair } from '@journey/contracts';

const mockLoadStoredSession = jest.fn();
const mockSaveStoredSession = jest.fn();
const mockClearStoredSession = jest.fn();

jest.mock('@/config/environment', () => ({ getApiBaseUrl: () => 'http://127.0.0.1:8000' }));
jest.mock('@/lib/session-storage', () => ({
  loadStoredSession: (...args: unknown[]) => mockLoadStoredSession(...args),
  saveStoredSession: (...args: unknown[]) => mockSaveStoredSession(...args),
  clearStoredSession: (...args: unknown[]) => mockClearStoredSession(...args),
}));

import {
  ApiNetworkError,
  analyzeFoodImage,
  confirmAgentCandidate,
  createRecord,
  deleteRecord,
  fetchApiHealth,
  fetchGoal,
  fetchHomeToday,
  fetchJourney,
  fetchProfile,
  listActivityRecords,
  listFoodRecords,
  listWeightRecords,
  login,
  logout,
  refreshSession,
  register,
  restoreSession,
  resumeAgentRun,
  runAgent,
  saveGoal,
  updateProfile,
  updateRecord,
} from '@/lib/api';

const session: TokenPair = {
  token_type: 'bearer',
  access_token: 'access-test',
  access_expires_at: '2099-01-01T00:00:00Z',
  refresh_token: 'refresh-test',
  refresh_expires_at: '2099-02-01T00:00:00Z',
  user: { id: 'user-1', status: 'active', identities: [], created_at: '2026-07-20T00:00:00Z' },
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('API client', () => {
  beforeEach(() => {
    jest.resetAllMocks();
    mockLoadStoredSession.mockResolvedValue(session);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('login omits bearer token and persists the returned session', async () => {
    const fetchMock = jest.spyOn(global, 'fetch').mockResolvedValue(jsonResponse(session));
    await expect(login({ identifier: 'demo@example.com', password: 'JourneyPass2026' })).resolves.toEqual(session);
    const [, init] = fetchMock.mock.calls[0]!;
    expect(new Headers(init?.headers).has('Authorization')).toBe(false);
    expect(mockSaveStoredSession).toHaveBeenCalledWith(session);
  });

  test('authenticated Agent request sends bearer token and structured body', async () => {
    const response = { run_id: 'run-1', candidates: [], citations: [], intents: [], events: [] };
    const fetchMock = jest.spyOn(global, 'fetch').mockResolvedValue(jsonResponse(response));
    await expect(runAgent('睡眠如何影响恢复？')).resolves.toEqual(response);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('http://127.0.0.1:8000/api/v1/agent/runs');
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer access-test');
    expect(JSON.parse(String(init?.body))).toEqual({ message: '睡眠如何影响恢复？' });

    fetchMock.mockResolvedValueOnce(jsonResponse(response));
    await runAgent('那接下来呢？', 'thread-1');
    expect(JSON.parse(String(fetchMock.mock.calls[1]![1]?.body))).toEqual({
      message: '那接下来呢？', thread_id: 'thread-1',
    });
  });

  test('stable API error envelope and network failure stay distinguishable', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValueOnce(jsonResponse({
      error: { code: 'validation_error', message: '参数错误', details: [] },
      request_id: 'request-1',
    }, 422));
    await expect(runAgent('x')).rejects.toMatchObject({ code: 'validation_error', status: 422 });

    jest.spyOn(global, 'fetch').mockRejectedValueOnce(new TypeError('offline'));
    await expect(runAgent('x')).rejects.toBeInstanceOf(ApiNetworkError);
  });

  test('session refresh, restore and logout use the stored refresh token', async () => {
    const fetchMock = jest.spyOn(global, 'fetch').mockImplementation(async () => jsonResponse(session));
    await expect(refreshSession({ refresh_token: 'refresh-test' })).resolves.toEqual(session);
    expect(mockSaveStoredSession).toHaveBeenCalledWith(session);

    mockLoadStoredSession.mockResolvedValueOnce({ ...session, access_expires_at: '2000-01-01T00:00:00Z' });
    await expect(restoreSession()).resolves.toEqual(session);

    fetchMock.mockResolvedValueOnce(jsonResponse({ message: 'ok' }));
    await logout();
    expect(mockClearStoredSession).toHaveBeenCalled();
  });

  test('expired refresh token clears local session without a request', async () => {
    mockLoadStoredSession.mockResolvedValue({ ...session, refresh_expires_at: '2000-01-01T00:00:00Z' });
    await expect(restoreSession()).resolves.toBeNull();
    expect(mockClearStoredSession).toHaveBeenCalled();
  });

  test('all public contract wrappers keep their paths and methods callable', async () => {
    const fetchMock = jest.spyOn(global, 'fetch').mockImplementation(async () => jsonResponse({ ok: true }));
    await register({ email: 'a@example.com', username: 'stage7', password: 'JourneyPass2026', display_name: 'Stage 7' });
    await fetchProfile();
    await updateProfile({ display_name: 'Stage 7' });
    await fetchGoal();
    await saveGoal({ kind: 'maintain' });
    await fetchHomeToday();
    await fetchJourney(30, '2026-07-01');
    await createRecord('food', { recorded_at: '2026-07-20T00:00:00Z', meal_type: 'other', name: '苹果', energy_kcal: 88 }, 'food-key');
    await updateRecord('food', 'food-1', { energy_kcal: 90 });
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await deleteRecord('food', 'food-1');
    await listFoodRecords();
    await listActivityRecords();
    await listWeightRecords();
    await confirmAgentCandidate('candidate-1', {
      confirmation_token: 'confirmation-token-long-enough',
      kind: 'weight',
      payload: { measured_at: '2026-07-20T00:00:00Z', weight_kg: 65 },
    }, 'candidate-key');
    await resumeAgentRun('run-1');
    await analyzeFoodImage({
      image_base64: '/9j/4EpvdXJuZXk=',
      media_type: 'image/jpeg',
      width: 640,
      height: 480,
      meal_type_hint: 'other',
      confirm_upload: true,
    });
    await fetchApiHealth();
    expect(fetchMock).toHaveBeenCalled();
  });
});
