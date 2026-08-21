const mockValues = new Map<string, string>();
const mockSecureValues = new Map<string, string>();

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
    generate: async () => ({ encoded: async () => 'account-test-key' }),
    import: async () => ({ encoded: async () => 'account-test-key' }),
  },
  AESSealedData: { fromCombined: (value: string) => ({ value }) },
  aesEncryptAsync: async (plaintext: Uint8Array) => ({
    combined: async () => Buffer.from(plaintext).toString('base64'),
  }),
  aesDecryptAsync: async (sealed: { value: string }) =>
    new Uint8Array(Buffer.from(sealed.value, 'base64')),
}));

import type { JourneyProfile, WeightRecord } from '@journey/contracts';

import { estimateRestingEnergy } from '@/lib/energy';

import {
  applyOptimisticMutation,
  conflictFields,
  emptyLocalReplica,
  journeyFromReplica,
  makeLocalRecord,
  mergeServerSnapshot,
  purgeLocalReplica,
  readLocalReplica,
  type LocalMutation,
  writeLocalReplica,
} from '@/lib/local-replica';

function profile(ownerUserId: string, name: string): JourneyProfile {
  return {
    user_id: ownerUserId,
    display_name: name,
    timezone: 'Asia/Shanghai',
    locale: 'zh-CN',
    sex: null,
    birth_date: null,
    height_cm: null,
    preferred_unit: 'metric',
    latest_weight_kg: null,
    version: 1,
    updated_at: '2026-08-05T00:00:00Z',
  };
}

describe('account-isolated encrypted local replica', () => {
  beforeEach(() => {
    mockValues.clear();
    mockSecureValues.clear();
  });

  test('uses separate data and key entries and purges only the signed-out account', async () => {
    const first = emptyLocalReplica('user-a');
    first.profile = profile('user-a', '账户甲私密画像');
    const second = emptyLocalReplica('user-b');
    second.profile = profile('user-b', '账户乙私密画像');

    await writeLocalReplica(first);
    await writeLocalReplica(second);

    expect([...mockValues.values()].join('')).not.toContain('私密画像');
    expect([...mockValues.keys()].some((key) => key.endsWith('.user-a'))).toBe(true);
    expect([...mockValues.keys()].some((key) => key.endsWith('.user-b'))).toBe(true);
    expect([...mockSecureValues.keys()].some((key) => key.endsWith('.user-a'))).toBe(true);
    expect([...mockSecureValues.keys()].some((key) => key.endsWith('.user-b'))).toBe(true);

    await purgeLocalReplica('user-a');
    await expect(readLocalReplica('user-a')).resolves.toMatchObject({ profile: null });
    await expect(writeLocalReplica(first)).rejects.toThrow('账户已退出');
    await expect(readLocalReplica('user-b')).resolves.toMatchObject({
      profile: { display_name: '账户乙私密画像' },
    });
  });

  test('reapplies pending edits after a server pull and derives Journey offline', () => {
    const replica = emptyLocalReplica('user-a');
    replica.profile = profile('user-a', 'Journey User');
    const server = makeLocalRecord('weight', {
      measured_at: '2026-08-05T07:00:00+08:00',
      weight_kg: 65,
    }, 'weight-1') as WeightRecord;
    server.version = 1;
    const local = { ...server, weight_kg: 64.8 };
    const mutation: LocalMutation = {
      id: 'mutation-1',
      ownerUserId: 'user-a',
      entity: 'weight',
      operation: 'update',
      resourceId: server.id,
      expectedVersion: 1,
      idempotencyKey: 'key-1',
      payload: { weight_kg: 64.8 },
      base: server as unknown as Record<string, unknown>,
      local: local as unknown as Record<string, unknown>,
      createdAt: '2026-08-05T08:00:00Z',
      attempts: 0,
    };
    replica.outbox.push(mutation);
    applyOptimisticMutation(replica, mutation);

    const merged = mergeServerSnapshot(replica, {
      profile: replica.profile,
      goal: null,
      records: { food: [], activity: [], weight: [server] },
    });
    const journey = journeyFromReplica(merged, 7);
    expect(journey.items[0]?.weight_records[0]?.weight_kg).toBe(64.8);
    expect(merged.outbox).toHaveLength(1);
  });

  test('reports field-level differences for an explainable conflict', () => {
    const mutation = {
      operation: 'update',
      payload: { weight_kg: 64.8, note: '本机' },
      local: { weight_kg: 64.8, note: '本机' },
    } as unknown as LocalMutation;
    expect(conflictFields(mutation, { weight_kg: 65.2, note: '云端' }))
      .toEqual(['weight_kg', 'note']);
  });

  test('derives the same explainable resting estimate offline without default profile values', () => {
    const complete = {
      ...profile('user-a', 'Journey User'),
      sex: 'male' as const,
      birth_date: '2000-08-13',
      height_cm: 170,
    };
    expect(estimateRestingEnergy(complete, 70.5, '2026-07-17')).toMatchObject({
      status: 'available', kcal_per_day: 1647.5, age_years: 25,
    });
    expect(estimateRestingEnergy(profile('user-a', 'Journey User'), null, '2026-07-17'))
      .toMatchObject({ status: 'missing_profile', kcal_per_day: null });
  });
});
