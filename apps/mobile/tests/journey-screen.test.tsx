import { fireEvent, render, waitFor } from '@testing-library/react-native';
import type { ReactNode } from 'react';

import type {
  AgentSummaryResponse,
  Goal,
  HomeToday,
  JourneyResponse,
} from '@journey/contracts';

const mockUseQuery = jest.fn();
const mockGenerateJourneySummary = jest.fn();
const mockFetchJourney = jest.fn();
const mockFetchGoal = jest.fn();
const mockFetchHome = jest.fn();

const mockSyncState = {
  isOnline: true,
  fetchJourney: (...args: unknown[]) => mockFetchJourney(...args),
  fetchGoal: (...args: unknown[]) => mockFetchGoal(...args),
  fetchHome: (...args: unknown[]) => mockFetchHome(...args),
};

jest.mock('@tanstack/react-query', () => ({
  useQuery: (options: unknown) => mockUseQuery(options),
}));
jest.mock('expo-router', () => ({ router: { push: jest.fn() } }));
jest.mock('@/providers/sync-provider', () => ({ useSync: () => mockSyncState }));
jest.mock('@/theme/theme-provider', () => ({
  useJourneyTheme: () => ({ colors: {
    background: '#F4FBF7', surface: '#FFFFFF', hero: '#DDF5E8', border: '#CCE2D7',
    primary: '#2F9E73', primaryStrong: '#247A59', text: '#163228', textMuted: '#587067',
    danger: '#C94B4B', dangerSoft: '#FDE7E7', warning: '#9A6A00', warningSoft: '#FFF3CF',
    info: '#2776A8', infoSoft: '#E4F3FC', food: '#E56B83',
  } }),
}));
jest.mock('@/components/screen-shell', () => ({
  ScreenShell: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
jest.mock('@/lib/api', () => {
  class ApiError extends Error {}
  class ApiNetworkError extends Error {}
  return {
    ApiError,
    ApiNetworkError,
    generateJourneySummary: (...args: unknown[]) => mockGenerateJourneySummary(...args),
  };
});

import JourneyScreen from '@/app/(tabs)/journey';

const journey: JourneyResponse = {
  items: Array.from({ length: 9 }, (_, index) => ({
    date: new Date(Date.UTC(2026, 8, 2 - index)).toISOString().slice(0, 10),
    intake_kcal: 0,
    activity_kcal: 0,
    net_kcal: 0,
    food_records: [],
    activity_records: [],
    weight_records: [],
  })),
  next_cursor: null,
  has_more: false,
};
const goal: Goal = {
  id: 'goal-1', kind: 'lose_fat', target_weight_kg: 65, daily_energy_target_kcal: 2000,
  starts_on: '2026-09-01', target_date: null, is_active: true, version: 1,
  updated_at: '2026-09-02T00:00:00Z',
};
const home: HomeToday = {
  date: '2026-09-02', timezone: 'Asia/Shanghai', intake_kcal: 0, activity_kcal: 0,
  net_kcal: 0, resting_energy: { status: 'available', kcal_per_day: 1800,
    formula: 'mifflin-st-jeor-1990', age_years: 24, missing_fields: [], note: '估算值' },
  estimated_energy_balance_kcal: -1800, counts: { food: 0, activity: 0, weight: 0 },
  latest_weight_kg: 70, active_goal: goal,
};
const aiSummary: AgentSummaryResponse = {
  period_days: 30,
  generated_at: '2026-09-02T08:00:00Z',
  cache_hit: false,
  statistics: {
    last_30_days: {
      period_days: 30, start_date: '2026-08-04', end_date: '2026-09-02', record_count: 18,
      food_count: 10, activity_count: 6, weight_count: 2, total_intake_kcal: 8600,
      total_activity_kcal: 1400, days_with_records: 9, weight_change_kg: -0.6,
    },
    last_7_days: {
      period_days: 7, start_date: '2026-08-27', end_date: '2026-09-02', record_count: 7,
      food_count: 4, activity_count: 2, weight_count: 1, total_intake_kcal: 3300,
      total_activity_kcal: 500, days_with_records: 4, weight_change_kg: null,
    },
    goal: { kind: 'lose_fat', target_weight_kg: 65, daily_energy_target_kcal: 2000 },
  },
  content: {
    headline: '近30天记录开始形成趋势，但完整度仍可提升。',
    key_findings: [
      {
        title: '记录完整度还不够',
        evidence: '近30天有9个记录日，近7天有4个记录日。',
        interpretation: '当前热量均值可能被漏记低估，暂不适合继续下调目标。',
      },
      {
        title: '运动已经启动',
        evidence: '近30天完成6次活动，近7天完成2次。',
        interpretation: '先固定频率，比继续提高单次消耗更容易形成节奏。',
      },
    ],
    next_7_days: [
      {
        title: '补齐5天饮食记录',
        plan: '未来7天至少记录5天，每天覆盖2餐。',
        reason: '完整记录后才能判断摄入是否真的低于目标。',
        success_metric: '7天后记录日≥5天，其中4天记录≥2餐。',
      },
      {
        title: '安排3次运动',
        plan: '完成2次30分钟中等强度和1次20分钟轻松活动。',
        reason: '固定周频率比追求单次热量更容易持续。',
        success_metric: '7天后完成3次活动，总时长≥80分钟。',
      },
    ],
  },
  citations: [{
    chunk_id: 'chunk-1', document_id: 'doc-1', source_slug: 'journey-core',
    title: '均衡饮食与记录', source_url: 'https://example.com', version: '1.0.0',
    region: 'global', score: 0.9, excerpt: '规律记录有助于观察长期趋势。',
  }],
  fallback_used: false,
  usage: { provider: 'mock', model: 'mock', input_tokens: 10, output_tokens: 20,
    retries: 0, latency_ms: 8, estimated_cost_usd: 0 },
};

const sevenDaySummary: AgentSummaryResponse = {
  ...aiSummary,
  period_days: 7,
  generated_at: '2026-09-03T03:30:00Z',
  statistics: {
    ...aiSummary.statistics,
    last_7_days: {
      ...aiSummary.statistics.last_7_days,
      record_count: 7,
      days_with_records: 4,
    },
  },
  content: {
    headline: '近7天已有稳定记录，可以开始调整下一步行动。',
    key_findings: [
      {
        title: '样本仍不完整',
        evidence: '近7天有4天记录，饮食与运动都已开始记录。',
        interpretation: '暂不根据当前均值继续减少热量。',
      },
      {
        title: '已有运动基础',
        evidence: '近7天完成2次活动。',
        interpretation: '下一步应先把运动次数固定下来。',
      },
    ],
    next_7_days: [
      {
        title: '补齐5天记录',
        plan: '未来7天至少记录5天，每天覆盖2餐。',
        reason: '减少漏记后才能判断真实摄入。',
        success_metric: '7天后记录日≥5天。',
      },
      {
        title: '安排3次运动',
        plan: '完成2次30分钟中等强度和1次20分钟轻松活动。',
        reason: '固定频率比追求单次消耗更容易持续。',
        success_metric: '7天后完成3次活动，总时长≥80分钟。',
      },
    ],
  },
};

describe('Journey period-aware AI summary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSyncState.isOnline = true;
    mockFetchJourney.mockResolvedValue(journey);
    mockFetchGoal.mockResolvedValue(goal);
    mockFetchHome.mockResolvedValue(home);
    mockGenerateJourneySummary.mockImplementation((period: 7 | 30) => Promise.resolve(
      period === 7 ? sevenDaySummary : aiSummary,
    ));
    mockUseQuery.mockImplementation(({ queryKey }: { queryKey: string[] }) => {
      if (queryKey[0] === 'journey') return { isLoading: false, isError: false, data: journey, refetch: jest.fn() };
      if (queryKey[0] === 'goal') return { isLoading: false, isError: false, data: goal, refetch: jest.fn() };
      return { isLoading: false, isError: false, data: home, refetch: jest.fn() };
    });
  });

  test('keeps 7-day and 30-day summaries independent and closes only the active period', async () => {
    const screen = await render(<JourneyScreen />);
    expect(screen.getByText('AI 7天总结')).toBeTruthy();
    expect(screen.queryByText(aiSummary.content.headline)).toBeNull();

    await fireEvent.press(screen.getByRole('button', { name: '近 30 天' }));
    expect(screen.getByText('AI 30天总结')).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '生成AI 30天总结' }));
    await waitFor(() => expect(screen.getByText(aiSummary.content.headline)).toBeTruthy());

    expect(mockGenerateJourneySummary).toHaveBeenCalledWith(30);
    expect(screen.getByText(/生成于/)).toBeTruthy();
    expect(screen.getByText('数据概览')).toBeTruthy();
    expect(screen.getByText('18 条')).toBeTruthy();
    expect(screen.getByText('AI发现')).toBeTruthy();
    expect(screen.getByText('接下来7天')).toBeTruthy();
    expect(screen.getByText('运动已经启动')).toBeTruthy();
    expect(screen.getByText('证据：近30天完成6次活动，近7天完成2次。')).toBeTruthy();
    expect(screen.getByText('验收：7天后完成3次活动，总时长≥80分钟。')).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: '近 7 天' }));
    expect(screen.getByText('AI 7天总结')).toBeTruthy();
    expect(screen.queryByText(aiSummary.content.headline)).toBeNull();
    expect(screen.getByRole('button', { name: '生成AI 7天总结' })).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: '近 30 天' }));
    expect(screen.getByText(aiSummary.content.headline)).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: '关闭AI 30天总结' }));
    expect(screen.queryByText(aiSummary.content.headline)).toBeNull();
    expect(screen.getByRole('button', { name: '生成AI 30天总结' })).toBeTruthy();
  });

  test('generates actionable 7-day guidance once two recorded days are available', async () => {
    const screen = await render(<JourneyScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '生成AI 7天总结' }));
    await waitFor(() => expect(screen.getByText(sevenDaySummary.content.headline)).toBeTruthy());

    expect(mockGenerateJourneySummary).toHaveBeenCalledWith(7);
    expect(screen.getByText('样本仍不完整')).toBeTruthy();
    expect(screen.getByText('意味着：暂不根据当前均值继续减少热量。')).toBeTruthy();
    expect(screen.getByText(/补齐5天记录/)).toBeTruthy();
    expect(screen.getByText('验收：7天后记录日≥5天。')).toBeTruthy();
    expect(screen.queryByText(/无法评估/)).toBeNull();
  });

  test('shows the different 7-day and 30-day recording thresholds before generation', async () => {
    mockUseQuery.mockImplementation(({ queryKey }: { queryKey: Array<string | number> }) => {
      if (queryKey[0] === 'journey') {
        const days = queryKey[1] === 7 ? 1 : 5;
        return { isLoading: false, isError: false, data: { ...journey, items: journey.items.slice(0, days) }, refetch: jest.fn() };
      }
      if (queryKey[0] === 'goal') return { isLoading: false, isError: false, data: goal, refetch: jest.fn() };
      return { isLoading: false, isError: false, data: home, refetch: jest.fn() };
    });
    const screen = await render(<JourneyScreen />);
    expect(screen.getByText('还差 1 天')).toBeTruthy();
    expect(screen.getByText(/至少需要2天/)).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: '近 30 天' }));
    expect(screen.getByText('还差 2 天')).toBeTruthy();
    expect(screen.getByText(/至少需要7天/)).toBeTruthy();
    expect(mockGenerateJourneySummary).not.toHaveBeenCalled();
  });

  test('keeps knowledge details folded until requested', async () => {
    const screen = await render(<JourneyScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '生成AI 7天总结' }));
    await waitFor(() => expect(screen.getByText('知识依据 1 条')).toBeTruthy());

    expect(screen.queryByText('规律记录有助于观察长期趋势。')).toBeNull();
    await fireEvent.press(screen.getByText('知识依据 1 条'));
    expect(screen.getByText('均衡饮食与记录 · v1.0.0')).toBeTruthy();
    expect(screen.getByText('规律记录有助于观察长期趋势。')).toBeTruthy();
  });
});
