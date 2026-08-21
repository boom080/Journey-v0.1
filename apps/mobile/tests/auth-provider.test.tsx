import { act, render, waitFor } from '@testing-library/react-native';

import type { TokenPair } from '@journey/contracts';

const mockQueryClear = jest.fn();
const mockQueryClient = { clear: mockQueryClear };
const mockClearPending = jest.fn().mockResolvedValue(undefined);
const mockPurgeReplica = jest.fn().mockResolvedValue(undefined);
const mockRestoreSession = jest.fn();
let mockSessionListener: ((value: TokenPair | null) => void) | undefined;

function session(ownerUserId: string): TokenPair {
  return {
    token_type: 'bearer',
    access_token: `access-${ownerUserId}`,
    access_expires_at: '2099-01-01T00:00:00Z',
    refresh_token: `refresh-${ownerUserId}`,
    refresh_expires_at: '2099-02-01T00:00:00Z',
    user: {
      id: ownerUserId,
      status: 'active',
      identities: [],
      created_at: '2026-08-05T00:00:00Z',
    },
  };
}

const mockFirstSession = session('account-a');
const mockSecondSession = session('account-b');

jest.mock('@tanstack/react-query', () => ({
  useQueryClient: () => mockQueryClient,
}));
jest.mock('@/lib/pending-storage', () => ({
  clearPendingMutationsForUser: (...args: unknown[]) => mockClearPending(...args),
}));
jest.mock('@/lib/local-replica', () => ({
  purgeLocalReplica: (...args: unknown[]) => mockPurgeReplica(...args),
}));
jest.mock('@/lib/api', () => ({
  login: jest.fn(),
  logout: jest.fn(),
  register: jest.fn(),
  restoreSession: (...args: unknown[]) => mockRestoreSession(...args),
  subscribeToSession: (listener: (value: TokenPair | null) => void) => {
    mockSessionListener = listener;
    return jest.fn();
  },
}));

import { AuthProvider, useAuth } from '@/providers/auth-provider';

let currentSession: TokenPair | null = null;

function Harness() {
  currentSession = useAuth().session;
  return null;
}

describe('AuthProvider local data cleanup', () => {
  beforeEach(() => {
    mockQueryClear.mockClear();
    mockClearPending.mockClear();
    mockPurgeReplica.mockClear();
    mockRestoreSession.mockReset().mockResolvedValue(mockFirstSession);
    mockSessionListener = undefined;
    currentSession = null;
  });

  test('purges the previous account when a live session switches owners', async () => {
    await render(<AuthProvider><Harness /></AuthProvider>);
    await waitFor(() => expect(currentSession?.user.id).toBe('account-a'));

    await act(async () => { mockSessionListener?.(mockSecondSession); });

    await waitFor(() => expect(currentSession?.user.id).toBe('account-b'));
    await waitFor(() => expect(mockClearPending).toHaveBeenCalledWith('account-a'));
    expect(mockPurgeReplica).toHaveBeenCalledWith('account-a');
    expect(mockQueryClear).toHaveBeenCalled();
  });
});
