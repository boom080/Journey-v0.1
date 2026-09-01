import { act, fireEvent, render, waitFor } from '@testing-library/react-native';

const mockUseLocalSearchParams = jest.fn();
const mockQueryClient = { invalidateQueries: jest.fn(), setQueryData: jest.fn(), removeQueries: jest.fn() };
const mockConfirmAgentCandidate = jest.fn();
const mockRouterBack = jest.fn();
const mockSyncState = { isOnline: true, updateRecord: jest.fn(), submitRecord: jest.fn(), deleteRecord: jest.fn() };
const mockAgentDataDeletedListeners = new Set<() => void>();
let mockDeletionGeneration = 0;

jest.mock('@tanstack/react-query', () => ({ useQueryClient: () => mockQueryClient }));
jest.mock('expo-router', () => ({
  router: { back: (...args: unknown[]) => mockRouterBack(...args) },
  useLocalSearchParams: (...args: unknown[]) => mockUseLocalSearchParams(...args),
}));
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
  ApiError: class ApiError extends Error {
    code: string;
    constructor(message: string, code: string) { super(message); this.code = code; }
  },
  confirmAgentCandidate: (...args: unknown[]) => mockConfirmAgentCandidate(...args),
  fetchAgentRunTrace: jest.fn(),
  getAgentDataRevision: () => mockDeletionGeneration,
  getAgentErrorMessage: (error: unknown) => error instanceof Error ? error.message : '保存失败',
  resumeAgentRun: jest.fn(),
  subscribeToAgentDataDeleted: (listener: () => void) => {
    mockAgentDataDeletedListeners.add(listener);
    return () => mockAgentDataDeletedListeners.delete(listener);
  },
}));

import RecordFormScreen from '@/app/record/[kind]';

const candidateParams = {
  kind: 'food', candidateId: 'candidate-1', confirmationToken: 'token-1', runId: 'run-1',
  name: '苹果', energy: '88', meal: 'lunch', timestamp: '2026-08-30T12:00:00Z',
};

describe('Agent candidate deletion invalidation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAgentDataDeletedListeners.clear();
    mockDeletionGeneration = 0;
    mockUseLocalSearchParams.mockReturnValue(candidateParams);
    mockSyncState.isOnline = true;
    mockConfirmAgentCandidate.mockResolvedValue({
      confirmation_progress: { total: 1, confirmed: 1, pending: 0, resume_available: false },
      resume_available: false,
    });
  });

  test('clears a mounted candidate draft and exits when Agent data is deleted', async () => {
    const screen = await render(<RecordFormScreen />);
    expect(screen.getByLabelText('食物名称').props.value).toBe('苹果');
    mockDeletionGeneration = 1;
    await act(async () => {
      mockAgentDataDeletedListeners.forEach((listener) => listener());
    });
    expect(mockRouterBack).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('食物名称').props.value).toBe('');
    expect(screen.queryByText(/这是 Agent 生成的候选/)).toBeNull();
  });

  test('does not write late confirmation results into Agent cache after deletion', async () => {
    let resolveConfirmation: ((value: unknown) => void) | undefined;
    mockConfirmAgentCandidate.mockImplementation(() => new Promise((resolve) => { resolveConfirmation = resolve; }));
    const screen = await render(<RecordFormScreen />);
    await fireEvent.press(screen.getByRole('button', { name: '确认候选并保存' }));
    await waitFor(() => expect(mockConfirmAgentCandidate).toHaveBeenCalled());

    mockDeletionGeneration = 1;
    await act(async () => {
      mockAgentDataDeletedListeners.forEach((listener) => listener());
    });
    await act(async () => {
      resolveConfirmation?.({
        confirmation_progress: { total: 1, confirmed: 1, pending: 0, resume_available: false },
        resume_available: false,
      });
    });
    expect(mockQueryClient.setQueryData).not.toHaveBeenCalled();
    expect(mockRouterBack).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('食物名称').props.value).toBe('');
  });
});
