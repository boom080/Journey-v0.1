import { fireEvent, render, waitFor } from '@testing-library/react-native';
import type { ReactNode } from 'react';

import type { AgentRunResponse, HomeToday } from '@journey/contracts';

const mockUseQuery = jest.fn();
const mockRunAgent = jest.fn();
const mockRouterPush = jest.fn();
const mockQueryClient = { getQueryData: jest.fn(), removeQueries: jest.fn() };
const mockSyncState = { isOnline: true, pendingCount: 0, status: 'idle' as const };

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
  return { ApiError, ApiNetworkError, fetchHomeToday: jest.fn(), resumeAgentRun: jest.fn(), runAgent: (...args: unknown[]) => mockRunAgent(...args) };
});

import HomeScreen from '@/app/(tabs)/index';

const emptyHome: HomeToday = {
  date: '2026-07-20', timezone: 'Asia/Shanghai', intake_kcal: 0, activity_kcal: 0,
  net_kcal: 0, counts: { food: 0, activity: 0, weight: 0 }, latest_weight_kg: null, active_goal: null,
};

const agentResponse: AgentRunResponse = {
  run_id: 'run-1', thread_id: 'thread-1', status: 'completed',
  intents: [{ intent: 'food', confidence: 0.99, segment: '午餐吃苹果 88 千卡' }],
  plan: {
    schema_version: '3', goal: '执行已校验的工具计划：food.parse_candidate',
    steps: [{ id: 'step-1', tool: 'food.parse_candidate', reason: '解析饮食候选', segment: null, depends_on: [], requires_confirmation: true }],
    needs_clarification: false, clarification_question: null,
  },
  step_results: [{ step_id: 'step-1', tool: 'food.parse_candidate', status: 'awaiting_confirmation', message: '等待用户确认', error_code: null }],
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
};

describe('Home page states and Agent candidate', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSyncState.isOnline = true;
    mockUseQuery.mockReturnValue({ isLoading: false, isError: false, data: emptyHome, refetch: jest.fn() });
    mockRunAgent.mockResolvedValue(agentResponse);
    delete process.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED;
  });

  test('hides the food image entry when the client feature flag is off', async () => {
    process.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED = 'false';
    const screen = await render(<HomeScreen />);
    expect(screen.queryByRole('button', { name: '📷 拍照估算饮食' })).toBeNull();
    expect(screen.getByText(/今天轻松记/)).toBeTruthy();
    expect(screen.getByLabelText('Journey 原版行走叶子吉祥物')).toBeTruthy();
  });

  test('renders empty state and a confirmed-write candidate without writing directly', async () => {
    const screen = await render(<HomeScreen />);
    expect(screen.getByText('今天还没有记录')).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '📷 拍照估算饮食' }));
    expect(mockRouterPush).toHaveBeenCalledWith('/food-image');
    await fireEvent.changeText(screen.getByLabelText('统一记录输入'), '午餐吃苹果 88 千卡');
    await fireEvent.press(screen.getByRole('button', { name: '理解并处理' }));
    await waitFor(() => expect(screen.getByText('苹果')).toBeTruthy());
    expect(screen.getByText('Agent 执行计划')).toBeTruthy();
    expect(screen.getByText('food.parse_candidate')).toBeTruthy();
    expect(screen.getByText(/连续对话线程/)).toBeTruthy();
    expect(screen.getByText(/当前使用 Mock/)).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '打开并确认候选' }));
    expect(mockRouterPush).toHaveBeenCalledWith(expect.objectContaining({ pathname: '/record/[kind]' }));
  });

  test('shows loading, API error, and offline Agent degradation explicitly', async () => {
    mockUseQuery.mockReturnValueOnce({ isLoading: true, isError: false, data: undefined, refetch: jest.fn() });
    const screen = await render(<HomeScreen />);
    expect(screen.getByText('正在同步今日数据…')).toBeTruthy();

    mockUseQuery.mockReturnValue({ isLoading: false, isError: true, data: undefined, refetch: jest.fn() });
    await screen.rerender(<HomeScreen />);
    expect(screen.getByText('今日数据暂时不可用')).toBeTruthy();

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
