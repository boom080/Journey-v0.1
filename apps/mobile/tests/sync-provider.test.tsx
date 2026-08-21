import { act, render, waitFor } from '@testing-library/react-native';
import type { PropsWithChildren } from 'react';

import type { TokenPair } from '@journey/contracts';

const mockValues = new Map<string, string>();
const mockSecureValues = new Map<string, string>();
const mockNetwork = { isConnected: false };
const mockInvalidateQueries = jest.fn().mockResolvedValue(undefined);
const mockSetQueryData = jest.fn();
const mockQueryClient = {
  invalidateQueries: mockInvalidateQueries,
  setQueryData: mockSetQueryData,
};
const mockApiCreateRecord = jest.fn();
const mockApiUpdateRecord = jest.fn();
const mockApiFetchProfile = jest.fn();
const mockApiFetchGoal = jest.fn();
const mockApiFetchJourney = jest.fn();

const mockSession: TokenPair = {
  token_type: 'bearer',
  access_token: 'access',
  access_expires_at: '2099-01-01T00:00:00Z',
  refresh_token: 'refresh',
  refresh_expires_at: '2099-02-01T00:00:00Z',
  user: {
    id: 'user-sync-a',
    status: 'active',
    identities: [],
    created_at: '2026-08-05T00:00:00Z',
  },
};

jest.mock('@react-native-community/netinfo', () => ({
  useNetInfo: () => mockNetwork,
}));
jest.mock('@tanstack/react-query', () => ({
  useQueryClient: () => mockQueryClient,
}));
jest.mock('@/providers/auth-provider', () => ({
  useAuth: () => ({ session: mockSession }),
}));
jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: async (key: string) => mockValues.get(key) ?? null,
  setItem: async (key: string, value: string) => { mockValues.set(key, value); },
  removeItem: async (key: string) => { mockValues.delete(key); },
}));
jest.mock('expo-secure-store', () => ({
  WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'device-only',
  getItemAsync: async (key: string) => mockSecureValues.get(key) ?? null,
  setItemAsync: async (key: string, value: string) => { mockSecureValues.set(key, value); },
  deleteItemAsync: async (key: string) => { mockSecureValues.delete(key); },
}));
jest.mock('expo-crypto', () => ({
  AESKeySize: { AES256: 256 },
  AESEncryptionKey: {
    generate: async () => ({ encoded: async () => 'sync-test-key' }),
    import: async () => ({ encoded: async () => 'sync-test-key' }),
  },
  AESSealedData: { fromCombined: (value: string) => ({ value }) },
  aesEncryptAsync: async (plaintext: Uint8Array) => ({
    combined: async () => Buffer.from(plaintext).toString('base64'),
  }),
  aesDecryptAsync: async (sealed: { value: string }) =>
    new Uint8Array(Buffer.from(sealed.value, 'base64')),
}));
jest.mock('@/lib/api', () => {
  class MockApiError extends Error {
    code: unknown;
    status: unknown;
    details: unknown;
    constructor(message: string, ...args: unknown[]) {
      super(message);
      [this.code, this.status, this.details] = args;
    }
  }
  class MockApiNetworkError extends Error {}
  return {
    ApiError: MockApiError,
    ApiNetworkError: MockApiNetworkError,
    createRecord: (...args: unknown[]) => mockApiCreateRecord(...args),
    deleteRecord: jest.fn(),
    fetchGoal: (...args: unknown[]) => mockApiFetchGoal(...args),
    fetchHomeToday: jest.fn(),
    fetchJourney: (...args: unknown[]) => mockApiFetchJourney(...args),
    fetchProfile: (...args: unknown[]) => mockApiFetchProfile(...args),
    saveGoal: jest.fn(),
    updateProfile: jest.fn(),
    updateRecord: (...args: unknown[]) => mockApiUpdateRecord(...args),
  };
});

import {
  applyOptimisticMutation,
  emptyLocalReplica,
  makeLocalRecord,
  readLocalReplica,
  type LocalMutation,
  writeLocalReplica,
} from '@/lib/local-replica';
import { ApiError } from '@/lib/api';
import { SyncProvider, useSync } from '@/providers/sync-provider';

let sync: ReturnType<typeof useSync> | null = null;

function Harness() {
  sync = useSync();
  return null;
}

function Wrapper({ children }: PropsWithChildren) {
  return <SyncProvider>{children}</SyncProvider>;
}

describe('offline record Outbox', () => {
  beforeEach(() => {
    mockValues.clear();
    mockSecureValues.clear();
    mockNetwork.isConnected = false;
    mockInvalidateQueries.mockClear();
    mockSetQueryData.mockClear();
    mockApiCreateRecord.mockReset();
    mockApiUpdateRecord.mockReset();
    mockApiFetchProfile.mockReset();
    mockApiFetchGoal.mockReset();
    mockApiFetchJourney.mockReset();
    mockApiFetchProfile.mockResolvedValue({
      user_id: mockSession.user.id,
      display_name: 'Sync User',
      timezone: 'Asia/Shanghai',
      locale: 'zh-CN',
      sex: null,
      birth_date: null,
      height_cm: null,
      preferred_unit: 'metric',
      latest_weight_kg: 65.2,
      version: 1,
      updated_at: '2026-08-05T00:00:00Z',
    });
    mockApiFetchGoal.mockResolvedValue(null);
    mockApiFetchJourney.mockResolvedValue({ items: [], next_cursor: null, has_more: false });
    sync = null;
  });

  test('coalesces an offline create/edit and cancels it on delete', async () => {
    await render(<Harness />, { wrapper: Wrapper });
    await waitFor(() => expect(sync?.status).toBe('offline'));

    let outcome: string | undefined;
    await act(async () => {
      outcome = await sync!.submitRecord('food', {
        recorded_at: '2026-08-05T12:00:00+08:00',
        meal_type: 'lunch',
        name: '本机午餐',
        energy_kcal: 500,
      });
    });
    expect(outcome).toBe('queued');
    let replica = await readLocalReplica(mockSession.user.id);
    expect(replica.outbox).toHaveLength(1);
    expect(replica.records.food[0]?.name).toBe('本机午餐');

    await act(async () => {
      outcome = await sync!.updateRecord('food', replica.records.food[0]!, {
        name: '本机午餐已修改',
      });
    });
    replica = await readLocalReplica(mockSession.user.id);
    expect(outcome).toBe('queued');
    expect(replica.outbox).toHaveLength(1);
    expect(replica.outbox[0]?.payload.name).toBe('本机午餐已修改');

    await act(async () => {
      outcome = await sync!.deleteRecord('food', replica.records.food[0]!);
    });
    replica = await readLocalReplica(mockSession.user.id);
    expect(outcome).toBe('saved');
    expect(replica.outbox).toEqual([]);
    expect(replica.records.food).toEqual([]);
  });

  test('automatically pushes an offline record after reconnect and reconciles the server snapshot', async () => {
    const screen = await render(<SyncProvider><Harness /></SyncProvider>);
    await waitFor(() => expect(sync?.status).toBe('offline'));

    const payload = {
      recorded_at: '2026-08-05T12:00:00+08:00',
      meal_type: 'lunch' as const,
      name: '断网牛肉面',
      energy_kcal: 550,
    };
    await act(async () => {
      expect(await sync!.submitRecord('food', payload)).toBe('queued');
    });
    expect((await readLocalReplica(mockSession.user.id)).outbox).toHaveLength(1);

    const serverRecord = makeLocalRecord('food', payload, 'food-server-after-reconnect');
    serverRecord.version = 1;
    mockApiCreateRecord.mockResolvedValue(serverRecord);
    mockApiFetchJourney.mockResolvedValue({
      items: [{
        date: '2026-08-05',
        intake_kcal: 550,
        activity_kcal: 0,
        net_kcal: 550,
        food_records: [serverRecord],
        activity_records: [],
        weight_records: [],
      }],
      next_cursor: null,
      has_more: false,
    });

    mockNetwork.isConnected = true;
    await screen.rerender(<SyncProvider><Harness /></SyncProvider>);

    await waitFor(() => expect(mockApiCreateRecord).toHaveBeenCalledTimes(1));
    await waitFor(async () => {
      const replica = await readLocalReplica(mockSession.user.id);
      expect(replica.outbox).toEqual([]);
      expect(replica.records.food).toMatchObject([
        { id: 'food-server-after-reconnect', name: '断网牛肉面', version: 1 },
      ]);
    });
    await waitFor(() => expect(sync?.status).toBe('idle'));
  });

  test('turns an offline server-record edit followed by delete into one delete mutation', async () => {
    const replica = emptyLocalReplica(mockSession.user.id);
    const serverRecord = makeLocalRecord('weight', {
      measured_at: '2026-08-05T07:00:00+08:00',
      weight_kg: 65,
    }, 'weight-server-1');
    serverRecord.version = 3;
    replica.records.weight = [serverRecord as never];
    await writeLocalReplica(replica);

    await render(<Harness />, { wrapper: Wrapper });
    await waitFor(() => expect(sync?.status).toBe('offline'));
    await act(async () => {
      await sync!.updateRecord('weight', serverRecord, { weight_kg: 64.8 });
    });
    let current = await readLocalReplica(mockSession.user.id);
    expect(current.outbox).toMatchObject([{ operation: 'update', expectedVersion: 3 }]);

    await act(async () => {
      await sync!.deleteRecord('weight', current.records.weight[0]!);
    });
    current = await readLocalReplica(mockSession.user.id);
    expect(current.outbox).toMatchObject([{ operation: 'delete', expectedVersion: 3 }]);
    expect(current.records.weight).toEqual([]);
  });

  test('stores only the last 90 calendar days from the profile timezone', async () => {
    const recentDate = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(new Date()).reduce<Record<string, string>>((parts, part) => {
      parts[part.type] = part.value;
      return parts;
    }, {});
    const today = `${recentDate.year}-${recentDate.month}-${recentDate.day}`;
    const recentWeight = makeLocalRecord('weight', {
      measured_at: `${today}T07:00:00+08:00`,
      weight_kg: 65,
    }, 'weight-recent');
    recentWeight.version = 1;
    const oldWeight = makeLocalRecord('weight', {
      measured_at: '2020-01-01T07:00:00+08:00',
      weight_kg: 70,
    }, 'weight-old');
    oldWeight.version = 1;
    mockApiFetchJourney.mockResolvedValue({
      items: [
        {
          date: today,
          intake_kcal: 0,
          activity_kcal: 0,
          net_kcal: 0,
          food_records: [],
          activity_records: [],
          weight_records: [recentWeight],
        },
        {
          date: '2020-01-01',
          intake_kcal: 0,
          activity_kcal: 0,
          net_kcal: 0,
          food_records: [],
          activity_records: [],
          weight_records: [oldWeight],
        },
      ],
      next_cursor: null,
      has_more: false,
    });
    mockNetwork.isConnected = true;

    await render(<Harness />, { wrapper: Wrapper });
    await waitFor(() => expect(mockApiFetchJourney).toHaveBeenCalledWith(30, undefined));
    await waitFor(async () => {
      const replica = await readLocalReplica(mockSession.user.id);
      expect(replica.records.weight.map((item) => item.id)).toEqual(['weight-recent']);
    });
  });

  test('pauses a stale update as a field-level conflict instead of overwriting the server', async () => {
    const replica = emptyLocalReplica(mockSession.user.id);
    const serverRecord = makeLocalRecord('weight', {
      measured_at: '2026-08-05T07:00:00+08:00',
      weight_kg: 65,
    }, 'weight-server-conflict');
    serverRecord.version = 3;
    replica.records.weight = [serverRecord as never];
    const mutation: LocalMutation = {
      id: 'mutation-conflict',
      ownerUserId: mockSession.user.id,
      entity: 'weight',
      operation: 'update',
      resourceId: serverRecord.id,
      expectedVersion: 3,
      idempotencyKey: 'update-conflict',
      payload: { weight_kg: 64.8 },
      base: serverRecord as unknown as Record<string, unknown>,
      local: { ...serverRecord, weight_kg: 64.8 } as unknown as Record<string, unknown>,
      createdAt: '2026-08-05T08:00:00Z',
      attempts: 0,
    };
    replica.outbox.push(mutation);
    applyOptimisticMutation(replica, mutation);
    await writeLocalReplica(replica);
    mockApiUpdateRecord.mockRejectedValue(new ApiError(
      'conflict',
      'sync_conflict',
      409,
      {
        resource_type: 'weight',
        resource_id: serverRecord.id,
        expected_version: 3,
        actual_version: 4,
        server: { ...serverRecord, weight_kg: 65.2, version: 4 },
      },
    ));
    mockNetwork.isConnected = true;
    const screen = await render(<SyncProvider><Harness /></SyncProvider>);
    await waitFor(() => expect(sync?.isOnline).toBe(true));
    await waitFor(() => expect(mockApiUpdateRecord).toHaveBeenCalled());
    await waitFor(() => expect(sync?.conflicts).toHaveLength(1));
    expect(sync?.conflicts[0]?.fields).toEqual(['weight_kg']);

    const conflictId = sync!.conflicts[0]!.id;
    mockNetwork.isConnected = false;
    await screen.rerender(<SyncProvider><Harness /></SyncProvider>);
    await act(async () => { await sync!.resolveConflict(conflictId, 'server'); });
    const resolved = await readLocalReplica(mockSession.user.id);
    expect(resolved.conflicts).toEqual([]);
    expect(resolved.records.weight[0]?.weight_kg).toBe(65.2);
  });
});
