import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import type { ReactNode } from 'react';

import type { AgentRunResponse, HomeToday } from '@journey/contracts';

const mockUseQuery = jest.fn();
const mockRunAgent = jest.fn();
const mockConfirmAgentCandidate = jest.fn();
const mockFetchAgentPrivacy = jest.fn();
const mockFetchAgentRunTrace = jest.fn();
const mockResumeAgentRun = jest.fn();
const mockHomeRefetch = jest.fn();
const mockFetchJourney = jest.fn();
const mockRouterPush = jest.fn();
const mockQueryClient = {
  getQueryData: jest.fn(),
  invalidateQueries: jest.fn(),
  removeQueries: jest.fn(),
};
const mockAgentDataDeletedListeners = new Set<() => void>();
const mockSyncState = {
  isOnline: true,
  pendingCount: 0,
  status: 'idle' as const,
  fetchJourney: (...args: unknown[]) => mockFetchJourney(...args),
};
let mockFoodImageEnabled = false;
let mockAgentDebugEnabled = false;

jest.mock('@tanstack/react-query', () => ({
  useQuery: (...args: unknown[]) => mockUseQuery(...args),
  useQueryClient: () => mockQueryClient,
}));
jest.mock('expo-router', () => ({
  router: { push: (...args: unknown[]) => mockRouterPush(...args) },
  useFocusEffect: jest.fn(),
}));
jest.mock('expo-image', () => ({ Image: require('react-native').Image }));
jest.mock('@/providers/sync-provider', () => ({ useSync: () => mockSyncState }));
jest.mock('@/theme/theme-provider', () => ({
  useJourneyTheme: () => ({ isDark: false, colors: {
    background: '#F4FBF7', surface: '#FFFFFF', hero: '#DDF5E8', border: '#CCE2D7',
    primary: '#2F9E73', primaryStrong: '#247A59', text: '#163228', textMuted: '#587067',
    danger: '#C94B4B', dangerSoft: '#FDE7E7', warning: '#9A6A00', warningSoft: '#FFF3CF',
    info: '#2776A8', infoSoft: '#E4F3FC', food: '#E56B83',
  }}),
}));
jest.mock('@/components/screen-shell', () => ({
  ScreenShell: ({ children, hero }: { children: ReactNode; hero?: ReactNode }) => <>{hero}{children}</>,
}));
jest.mock('@/lib/api', () => {
  class ApiError extends Error {}
  class ApiNetworkError extends Error {}
  return {
    ApiError,
    ApiNetworkError,
    confirmAgentCandidate: (...args: unknown[]) => mockConfirmAgentCandidate(...args),
    fetchHomeToday: jest.fn(),
    fetchAgentPrivacy: (...args: unknown[]) => mockFetchAgentPrivacy(...args),
    fetchAgentRunTrace: (...args: unknown[]) => mockFetchAgentRunTrace(...args),
    resumeAgentRun: (...args: unknown[]) => mockResumeAgentRun(...args),
    runAgent: (...args: unknown[]) => mockRunAgent(...args),
    subscribeToAgentDataDeleted: (listener: () => void) => {
      mockAgentDataDeletedListeners.add(listener);
      return () => mockAgentDataDeletedListeners.delete(listener);
    },
    getAgentErrorMessage: (error: unknown) => error instanceof Error ? error.message : 'Agent 暂时不可用，请稍后重试',
  };
});
jest.mock('@/config/environment', () => ({
  isFoodImageAnalysisEnabled: () => mockFoodImageEnabled,
  isAgentDebugDetailsEnabled: () => mockAgentDebugEnabled,
}));

import HomeScreen from '@/app/(tabs)/index';

const emptyHome: HomeToday = {
  date: '2026-07-20', timezone: 'Asia/Shanghai', intake_kcal: 0, activity_kcal: 0,
  net_kcal: 0,
  resting_energy: { status: 'missing_profile', kcal_per_day: null, formula: 'mifflin-st-jeor-1990', age_years: null, missing_fields: ['sex', 'birth_date', 'height_cm', 'weight_kg'], note: '补充资料后可估算。' },
  estimated_energy_balance_kcal: null,
  counts: { food: 0, activity: 0, weight: 0 }, latest_weight_kg: null, active_goal: null,
};

const agentResponse: AgentRunResponse = {
  run_id: 'run-1', thread_id: 'thread-1', status: 'waiting_for_user',
  intents: [{ intent: 'food', confidence: 0.99, segment: '午餐吃苹果 88 千卡' }],
  plan: {
    schema_version: '3', goal: '执行已校验的工具计划：food.parse_candidate',
    steps: [{ id: 'step-1', tool: 'food.parse_candidate', reason: '解析饮食候选', segment: null, depends_on: [], requires_confirmation: true, specialist: 'record_agent' }],
    needs_clarification: false, clarification_question: null,
  },
  step_results: [{ step_id: 'step-1', tool: 'food.parse_candidate', status: 'awaiting_confirmation', message: '等待用户确认', error_code: null, specialist: 'record_agent', duration_ms: 2 }],
  verification: { passed: true, completed_steps: 1, failed_steps: 0, skipped_steps: 0, replan_count: 0, reason: '所有计划步骤已完成或进入用户确认', decision: 'wait_for_user', waiting_for_user: true, pending_confirmations: 1 },
  observations: [], confirmation_progress: { total: 1, confirmed: 0, pending: 1, resume_available: false }, resumable: false,
  events: [],
  candidates: [{
    kind: 'food', candidate_id: 'candidate-1', confirmation_token: 'token',
    payload: { recorded_at: '2026-07-20T12:00:00Z', meal_type: 'lunch', name: '苹果', energy_kcal: 88 },
    explanation: '保存前可修改',
  }],
  answer: null, citations: [], fallback_used: true,
  safety_notice: '不提供医疗诊断或治疗建议。',
  usage: { provider: 'mock', model: 'journey-deterministic-v1', input_tokens: 10, output_tokens: 12, retries: 0, latency_ms: 5, estimated_cost_usd: 0 },
  selected_agents: ['orchestrator', 'record_agent'],
};

describe('Home page states and Agent candidate', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAgentDataDeletedListeners.clear();
    mockSyncState.isOnline = true;
    mockHomeRefetch.mockResolvedValue({ data: emptyHome });
    mockFetchJourney.mockResolvedValue({ items: [], next_cursor: null, has_more: false });
    mockQueryClient.invalidateQueries.mockResolvedValue(undefined);
    mockUseQuery.mockReturnValue({ isLoading: false, isError: false, data: emptyHome, refetch: mockHomeRefetch });
    mockFetchAgentPrivacy.mockResolvedValue({
      provider: 'journey-internal', external: false, enabled: true, policy_version: '2026-08-01',
      consent_granted: false, granted_at: null, retention_days: 30,
      notice: 'Agent 隐私说明', data_sent: [], provider_policy_url: null,
      provider_retention_notice: '不发送给第三方。', deletion_notice: '可删除 Agent 数据。',
    });
    mockRunAgent.mockResolvedValue(agentResponse);
    mockFoodImageEnabled = false;
    mockAgentDebugEnabled = false;
  });

  test('hides the food image entry when the runtime capability is off', async () => {
    const screen = await render(<HomeScreen />);
    expect(screen.queryByRole('button', { name: '📷 拍照估算饮食' })).toBeNull();
    expect(screen.getByText(/今天轻松记/)).toBeTruthy();
    expect(screen.getByLabelText('Journey 原版行走叶子吉祥物')).toBeTruthy();
  });

  test('renders inline defaults without exposing internal Agent details', async () => {
    mockFoodImageEnabled = true;
    mockAgentDebugEnabled = true;
    const screen = await render(<HomeScreen />);
    expect(screen.getByText('今天还没有记录')).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '📷 拍照估算饮食' }));
    expect(mockRouterPush).toHaveBeenCalledWith('/food-image');
    await fireEvent.changeText(screen.getByLabelText('统一记录输入'), '午餐吃苹果 88 千卡');
    await fireEvent.press(screen.getByRole('button', { name: '理解并处理' }));
    await waitFor(() => expect(screen.getByText('苹果')).toBeTruthy());
    expect(screen.getByRole('button', { name: '餐别：午餐，点击修改' })).toBeTruthy();
    expect(screen.getByText(/1 份 · 约 88 kcal/)).toBeTruthy();
    expect(screen.getByRole('button', { name: '确认并记录 1 条' })).toBeTruthy();
    expect(screen.queryByText('Agent 执行计划')).toBeNull();
    expect(screen.queryByText(/Orchestrator → Record Agent/)).toBeNull();
    expect(screen.queryByText(/food\.parse_candidate/)).toBeNull();
    expect(screen.queryByText(/连续对话线程/)).toBeNull();
    expect(screen.getByText(/这是估算结果/)).toBeTruthy();
  });

  test('updates the food meal inline before confirming the candidate', async () => {
    const snackResponse: AgentRunResponse = {
      ...agentResponse,
      candidates: [{
        kind: 'food',
        candidate_id: 'candidate-1',
        confirmation_token: 'token',
        payload: {
          recorded_at: '2026-07-20T12:00:00Z',
          meal_type: 'snack',
          name: '苹果',
          energy_kcal: 88,
        },
        explanation: '保存前可修改',
      }],
    };
    mockRunAgent.mockResolvedValueOnce(snackResponse);
    mockConfirmAgentCandidate.mockResolvedValueOnce({
      run_status: 'completed', resume_available: false,
      confirmation_progress: { total: 1, confirmed: 1, pending: 0, resume_available: false },
    });

    const screen = await render(<HomeScreen />);
    await fireEvent.changeText(screen.getByLabelText('统一记录输入'), '吃了苹果');
    await fireEvent.press(screen.getByRole('button', { name: '理解并处理' }));
    await waitFor(() => expect(screen.getByRole('button', { name: '餐别：加餐，点击修改' })).toBeTruthy());
    await fireEvent.press(screen.getByRole('button', { name: '餐别：加餐，点击修改' }));
    await fireEvent.press(screen.getByRole('button', { name: '午餐' }));
    expect(screen.getByRole('button', { name: '餐别：午餐，点击修改' })).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: '确认并记录 1 条' }));
    await waitFor(() => expect(mockConfirmAgentCandidate).toHaveBeenCalledTimes(1));
    expect(mockConfirmAgentCandidate).toHaveBeenCalledWith(
      'candidate-1',
      expect.objectContaining({
        kind: 'food',
        payload: expect.objectContaining({ meal_type: 'lunch' }),
      }),
      'agent-candidate-1',
    );
  });

  test('keeps internal Agent details out of the ordinary user result', async () => {
    const screen = await render(<HomeScreen />);
    await fireEvent.changeText(screen.getByLabelText('统一记录输入'), '午餐吃苹果 88 千卡');
    await fireEvent.press(screen.getByRole('button', { name: '理解并处理' }));
    await waitFor(() => expect(screen.getByText('苹果')).toBeTruthy());
    expect(screen.queryByText('Agent 执行计划')).toBeNull();
    expect(screen.queryByText(/Orchestrator → Record Agent/)).toBeNull();
    expect(screen.queryByText(/food\.parse_candidate/)).toBeNull();
    expect(screen.queryByText(/journey-deterministic-v1/)).toBeNull();
  });

  test('confirms food and activity with one button and refreshes today immediately', async () => {
    const multiIntent: AgentRunResponse = {
      ...agentResponse,
      intents: [
        { intent: 'food', confidence: 0.99, segment: '吃了牛肉面' },
        { intent: 'activity', confidence: 0.99, segment: '跑步三十分钟' },
      ],
      confirmation_progress: { total: 2, confirmed: 0, pending: 2, resume_available: false },
      candidates: [
        {
          kind: 'food', candidate_id: 'candidate-food', confirmation_token: 'token-food',
          payload: {
            recorded_at: '2026-09-02T04:00:00Z', meal_type: 'lunch', name: '牛肉面',
            portion_amount: 1, portion_unit: '碗', energy_kcal: 500,
          },
          explanation: '默认估算',
        },
        {
          kind: 'activity', candidate_id: 'candidate-activity', confirmation_token: 'token-activity',
          payload: {
            recorded_at: '2026-09-02T04:00:00Z', name: '跑步', activity_type: '跑步',
            duration_minutes: 30, intensity: 'moderate', energy_kcal: 300,
          },
          explanation: '默认估算',
        },
      ],
    };
    mockRunAgent.mockResolvedValueOnce(multiIntent);
    mockConfirmAgentCandidate
      .mockResolvedValueOnce({
        run_status: 'waiting_for_user', resume_available: false,
        confirmation_progress: { total: 2, confirmed: 1, pending: 1, resume_available: false },
      })
      .mockResolvedValueOnce({
        run_status: 'waiting_for_user', resume_available: true,
        confirmation_progress: { total: 2, confirmed: 2, pending: 0, resume_available: true },
      });
    mockResumeAgentRun.mockResolvedValueOnce({
      ...multiIntent,
      status: 'completed',
      candidates: [],
      answer: '近 7 天记录覆盖 2 天。',
      confirmation_progress: { total: 2, confirmed: 2, pending: 0, resume_available: false },
    });

    const screen = await render(<HomeScreen />);
    await fireEvent.changeText(screen.getByLabelText('统一记录输入'), '吃了牛肉面，跑步三十分钟');
    await fireEvent.press(screen.getByRole('button', { name: '理解并处理' }));
    await waitFor(() => expect(screen.getByRole('button', { name: '餐别：午餐，点击修改' })).toBeTruthy());
    expect(screen.getByText(/1 碗 · 约 500 kcal/)).toBeTruthy();
    expect(screen.getByText('30 分钟 · 适中 · 约 300 kcal')).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: '确认并记录 2 条' }));
    await waitFor(() => expect(mockConfirmAgentCandidate).toHaveBeenCalledTimes(2));
    expect(mockConfirmAgentCandidate).toHaveBeenNthCalledWith(
      1,
      'candidate-food',
      expect.objectContaining({ kind: 'food', payload: multiIntent.candidates[0]!.payload }),
      'agent-candidate-food',
    );
    expect(mockConfirmAgentCandidate).toHaveBeenNthCalledWith(
      2,
      'candidate-activity',
      expect.objectContaining({ kind: 'activity', payload: multiIntent.candidates[1]!.payload }),
      'agent-candidate-activity',
    );
    expect(mockResumeAgentRun).toHaveBeenCalledTimes(1);
    expect(mockResumeAgentRun).toHaveBeenCalledWith('run-1');
    await waitFor(() => expect(mockHomeRefetch).toHaveBeenCalled());
    expect(mockFetchJourney).toHaveBeenCalledWith(7, undefined, 7);
    expect(screen.getByText(/已记录 2 条，今天的变化已更新/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /确认并记录/ })).toBeNull();
    expect(mockRouterPush).not.toHaveBeenCalledWith(
      expect.objectContaining({ pathname: '/record/[kind]' }),
    );
  });

  test('keeps only the failed candidate available after a partial confirmation', async () => {
    const multiIntent: AgentRunResponse = {
      ...agentResponse,
      confirmation_progress: { total: 2, confirmed: 0, pending: 2, resume_available: false },
      candidates: [
        {
          kind: 'food', candidate_id: 'candidate-food', confirmation_token: 'token-food',
          payload: {
            recorded_at: '2026-09-02T04:00:00Z', meal_type: 'lunch', name: '牛肉面',
            portion_amount: 1, portion_unit: '碗', energy_kcal: 500,
          },
          explanation: '默认估算',
        },
        {
          kind: 'activity', candidate_id: 'candidate-activity', confirmation_token: 'token-activity',
          payload: {
            recorded_at: '2026-09-02T04:00:00Z', name: '跑步', activity_type: '跑步',
            duration_minutes: 30, intensity: 'moderate', energy_kcal: 300,
          },
          explanation: '默认估算',
        },
      ],
    };
    mockRunAgent.mockResolvedValueOnce(multiIntent);
    mockConfirmAgentCandidate
      .mockResolvedValueOnce({
        run_status: 'waiting_for_user', resume_available: false,
        confirmation_progress: { total: 2, confirmed: 1, pending: 1, resume_available: false },
      })
      .mockRejectedValueOnce(new Error('运动记录暂时失败'))
      .mockResolvedValueOnce({
        run_status: 'completed', resume_available: false,
        confirmation_progress: { total: 2, confirmed: 2, pending: 0, resume_available: false },
      });

    const screen = await render(<HomeScreen />);
    await fireEvent.changeText(screen.getByLabelText('统一记录输入'), '吃了牛肉面，跑步三十分钟');
    await fireEvent.press(screen.getByRole('button', { name: '理解并处理' }));
    await waitFor(() => expect(screen.getByRole('button', { name: '确认并记录 2 条' })).toBeTruthy());
    await fireEvent.press(screen.getByRole('button', { name: '确认并记录 2 条' }));

    await waitFor(() => expect(screen.getByText(/已记录 1\/2 条/)).toBeTruthy());
    expect(screen.queryByText('牛肉面')).toBeNull();
    expect(screen.getByText('跑步')).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '确认并记录 1 条' }));
    await waitFor(() => expect(mockConfirmAgentCandidate).toHaveBeenCalledTimes(3));
    expect(mockConfirmAgentCandidate).toHaveBeenNthCalledWith(
      3,
      'candidate-activity',
      expect.any(Object),
      'agent-candidate-activity',
    );
    expect(mockConfirmAgentCandidate.mock.calls.filter(([candidateId]) => candidateId === 'candidate-food')).toHaveLength(1);
  });

  test('checks external consent before the first online submission and sends no message when missing', async () => {
    mockFetchAgentPrivacy.mockResolvedValue({
      provider: 'example-ai', external: true, enabled: true, policy_version: 'policy-7',
      consent_granted: false, granted_at: null, retention_days: 30, notice: 'notice',
      data_sent: ['message'], provider_policy_url: null, provider_retention_notice: 'retention', deletion_notice: 'deletion',
    });
    const screen = await render(<HomeScreen />);
    await fireEvent.changeText(screen.getByLabelText('统一记录输入'), '午餐吃苹果 88 千卡');
    await fireEvent.press(screen.getByRole('button', { name: '理解并处理' }));
    await waitFor(() => expect(mockRouterPush).toHaveBeenCalledWith('/settings/agent-privacy'));
    expect(mockFetchAgentPrivacy).toHaveBeenCalledTimes(1);
    expect(mockRunAgent).not.toHaveBeenCalled();
    expect(screen.getByText(/消息尚未发送/)).toBeTruthy();
  });

  test('deletion notification clears the home Agent run, thread and candidates', async () => {
    const screen = await render(<HomeScreen />);
    await fireEvent.changeText(screen.getByLabelText('统一记录输入'), '午餐吃苹果 88 千卡');
    await fireEvent.press(screen.getByRole('button', { name: '理解并处理' }));
    await waitFor(() => expect(screen.getByText('苹果')).toBeTruthy());
    expect(mockAgentDataDeletedListeners.size).toBeGreaterThan(0);
    await act(async () => {
      mockAgentDataDeletedListeners.forEach((listener) => listener());
    });
    await waitFor(() => expect(screen.queryByText('苹果')).toBeNull());
    expect(mockQueryClient.removeQueries).toHaveBeenCalledWith(expect.objectContaining({ predicate: expect.any(Function) }));
  });

  test('does not rehydrate a late Agent response after deletion notification', async () => {
    let resolveRun: ((value: AgentRunResponse) => void) | undefined;
    mockRunAgent.mockImplementation(() => new Promise<AgentRunResponse>((resolve) => { resolveRun = resolve; }));
    const screen = await render(<HomeScreen />);
    await fireEvent.changeText(screen.getByLabelText('统一记录输入'), '午餐吃苹果 88 千卡');
    await fireEvent.press(screen.getByRole('button', { name: '理解并处理' }));
    await waitFor(() => expect(mockRunAgent).toHaveBeenCalled());
    await act(async () => {
      mockAgentDataDeletedListeners.forEach((listener) => listener());
    });
    await act(async () => {
      resolveRun?.(agentResponse);
    });
    await waitFor(() => expect(screen.queryByText('苹果')).toBeNull());
    expect(screen.queryByText('处理结果')).toBeNull();
  });

  test('shows loading, a friendly empty fallback, and offline Agent degradation explicitly', async () => {
    mockUseQuery.mockReturnValueOnce({ isLoading: true, isError: false, data: undefined, refetch: jest.fn() });
    const screen = await render(<HomeScreen />);
    expect(screen.getByText('正在同步今日数据…')).toBeTruthy();

    mockUseQuery.mockReturnValue({ isLoading: false, isError: true, data: undefined, refetch: jest.fn() });
    await screen.rerender(<HomeScreen />);
    expect(screen.getByText('今天还没有记录')).toBeTruthy();
    expect(screen.queryByText('今日数据暂时不可用')).toBeNull();
    expect(screen.queryByRole('button', { name: '重试' })).toBeNull();

    mockSyncState.isOnline = false;
    await screen.rerender(<HomeScreen />);
    expect(screen.getByLabelText('在线状态：离线 · 手动可用')).toBeTruthy();
    expect(screen.queryByText(/当前离线：/)).toBeNull();
    await fireEvent.changeText(screen.getByLabelText('统一记录输入'), '午餐吃苹果 88 千卡');
    await fireEvent.press(screen.getByRole('button', { name: '理解并处理' }));
    await waitFor(() => expect(screen.getByText(/离线时 Agent 不可用/)).toBeTruthy());
    expect(mockRunAgent).not.toHaveBeenCalled();
  });

  test('fills the unified input from warm quick suggestions', async () => {
    const screen = await render(<HomeScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '运动了 30 分钟' }));
    expect(screen.getByLabelText('统一记录输入').props.value).toBe('今天运动了 30 分钟');
  });
});
