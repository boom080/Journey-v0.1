import { fireEvent, render, waitFor } from '@testing-library/react-native';
import type { AgentPrivacyStatus } from '@journey/contracts';

const mockUseQuery = jest.fn();
const mockQueryClient = { removeQueries: jest.fn(), setQueryData: jest.fn() };
const mockFetchPrivacy = jest.fn();
const mockUpdateConsent = jest.fn();
const mockDeleteData = jest.fn();
const mockNotifyAgentDataDeleted = jest.fn();
const mockRouterBack = jest.fn();
const mockSyncState = { isOnline: true };
let mockStatus: AgentPrivacyStatus;

jest.mock('@tanstack/react-query', () => ({
  useQuery: (...args: unknown[]) => mockUseQuery(...args),
  useQueryClient: () => mockQueryClient,
}));
jest.mock('expo-router', () => ({ router: { back: (...args: unknown[]) => mockRouterBack(...args) } }));
jest.mock('@/providers/sync-provider', () => ({ useSync: () => mockSyncState }));
jest.mock('@/theme/theme-provider', () => ({
  useJourneyTheme: () => ({ isDark: false, colors: {
    background: '#F4FBF7', surface: '#FFFFFF', hero: '#DDF5E8', border: '#CCE2D7',
    primary: '#2F9E73', primaryStrong: '#247A59', text: '#163228', textMuted: '#587067',
    danger: '#C94B4B', dangerSoft: '#FDE7E7', warning: '#9A6A00', warningSoft: '#FFF3CF',
    info: '#2776A8', infoSoft: '#E4F3FC', food: '#E56B83',
  } }),
}));
jest.mock('@/lib/api', () => ({
  deleteAgentData: (...args: unknown[]) => mockDeleteData(...args),
  fetchAgentPrivacy: (...args: unknown[]) => mockFetchPrivacy(...args),
  getAgentErrorMessage: (error: unknown) => error instanceof Error ? error.message : '请求失败',
  notifyAgentDataDeleted: (...args: unknown[]) => mockNotifyAgentDataDeleted(...args),
  updateAgentConsent: (...args: unknown[]) => mockUpdateConsent(...args),
}));

import AgentPrivacySettingsScreen from '@/app/settings/agent-privacy';

function makeStatus(consentGranted = false): AgentPrivacyStatus {
  return {
    provider: 'example-ai', external: true, enabled: true, policy_version: 'policy-7',
    consent_granted: consentGranted, granted_at: consentGranted ? '2026-08-30T08:00:00Z' : null,
    retention_days: 30, notice: '外部 AI 仅用于处理你主动提交的消息。',
    data_sent: ['本次消息', '近 7 天结构化记录'], provider_policy_url: 'https://example.com/privacy',
    provider_retention_notice: '服务商最多保留 30 天。', deletion_notice: '删除会清除 Journey 侧 Agent Run 与线程。',
  };
}

describe('External AI and data privacy screen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSyncState.isOnline = true;
    mockStatus = makeStatus(false);
    mockUseQuery.mockImplementation(() => ({ isLoading: false, isError: false, error: null, data: mockStatus, refetch: jest.fn() }));
    mockFetchPrivacy.mockResolvedValue(mockStatus);
    mockUpdateConsent.mockResolvedValue({ ...mockStatus, consent_granted: true, granted_at: '2026-08-30T09:00:00Z' });
    mockDeleteData.mockResolvedValue({ deleted_runs: 2, deleted_threads: 1, consent_revoked: true, provider_data_deleted: false, message: '服务商侧请参阅其政策。' });
  });

  test('does not grant by default and requires an explicit selection and click', async () => {
    const screen = await render(<AgentPrivacySettingsScreen />);
    expect(screen.getAllByText('未授权').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: '我已阅读发送范围和保留规则' }).props.accessibilityState.selected).toBe(false);
    expect(mockUpdateConsent).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByRole('button', { name: '授权外部 AI' }));
    expect(mockUpdateConsent).not.toHaveBeenCalled();

    await fireEvent.press(screen.getByRole('button', { name: '我已阅读发送范围和保留规则' }));
    await fireEvent.press(screen.getByRole('button', { name: '授权外部 AI' }));
    await waitFor(() => expect(mockUpdateConsent).toHaveBeenCalledWith({ granted: true, policy_version: 'policy-7' }));
  });

  test('resets a pending consent selection when the server policy version changes', async () => {
    const screen = await render(<AgentPrivacySettingsScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '我已阅读发送范围和保留规则' }));
    expect(screen.getByRole('button', { name: '我已阅读发送范围和保留规则' }).props.accessibilityState.selected).toBe(true);

    mockStatus = { ...mockStatus, policy_version: 'policy-8' };
    await screen.rerender(<AgentPrivacySettingsScreen />);
    await waitFor(() => expect(screen.getByRole('button', { name: '我已阅读发送范围和保留规则' }).props.accessibilityState.selected).toBe(false));
  });

  test('requires a second confirmation before revoking consent', async () => {
    mockStatus = makeStatus(true);
    mockUpdateConsent.mockResolvedValue({ ...mockStatus, consent_granted: false, granted_at: null });
    const screen = await render(<AgentPrivacySettingsScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '撤回外部 AI 授权' }));
    expect(mockUpdateConsent).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByRole('button', { name: '确认撤回授权' }));
    await waitFor(() => expect(mockUpdateConsent).toHaveBeenCalledWith({ granted: false, policy_version: 'policy-7' }));
  });

  test('only clears Agent state after a confirmed successful deletion', async () => {
    mockStatus = makeStatus(true);
    mockDeleteData.mockRejectedValueOnce(new Error('网络不可用'));
    const screen = await render(<AgentPrivacySettingsScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '删除 Agent 数据' }));
    expect(mockDeleteData).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByRole('button', { name: '确认删除 Agent 数据' }));
    await waitFor(() => expect(screen.getByText('网络不可用')).toBeTruthy());
    expect(mockNotifyAgentDataDeleted).not.toHaveBeenCalled();

    mockDeleteData.mockResolvedValueOnce({ deleted_runs: 2, deleted_threads: 1, consent_revoked: true, provider_data_deleted: false, message: '删除完成。' });
    await fireEvent.press(screen.getByRole('button', { name: '确认删除 Agent 数据' }));
    await waitFor(() => expect(mockNotifyAgentDataDeleted).toHaveBeenCalledTimes(1));
    expect(mockQueryClient.removeQueries).toHaveBeenCalled();
    expect(screen.getByText(/已删除 Journey 侧 2 个 Run、1 个线程/)).toBeTruthy();
  });

  test('does not call privacy APIs while offline', async () => {
    mockSyncState.isOnline = false;
    mockUseQuery.mockImplementation(() => ({ isLoading: false, isError: false, error: null, data: undefined, refetch: jest.fn() }));
    const screen = await render(<AgentPrivacySettingsScreen />);
    expect(screen.getByText(/当前离线/)).toBeTruthy();
    expect(mockFetchPrivacy).not.toHaveBeenCalled();
    expect(mockUseQuery.mock.calls[0]![0]).toEqual(expect.objectContaining({ enabled: false }));
  });
});
