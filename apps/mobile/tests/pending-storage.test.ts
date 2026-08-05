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
    generate: async () => ({ encoded: async () => 'test-key' }),
    import: async () => ({ encoded: async () => 'test-key' }),
  },
  AESSealedData: {
    fromCombined: (value: string) => ({ value }),
  },
  aesEncryptAsync: async (plaintext: Uint8Array) => ({
    combined: async () => Buffer.from(plaintext).toString('base64'),
  }),
  aesDecryptAsync: async (sealed: { value: string }) =>
    new Uint8Array(Buffer.from(sealed.value, 'base64')),
}));

import type { PendingMutation } from '@journey/contracts';

import {
  clearAllPendingMutations,
  clearPendingMutationsForUser,
  readPendingMutations,
  writePendingMutations,
} from '@/lib/pending-storage';

function mutation(ownerUserId: string, createdAt = new Date().toISOString()): PendingMutation {
  return {
    id: `pending-${ownerUserId}`,
    ownerUserId,
    idempotencyKey: `key-${ownerUserId}`,
    kind: 'food',
    payload: {
      recorded_at: '2026-07-20T00:00:00Z',
      meal_type: 'other',
      name: '私密苹果',
      energy_kcal: 80,
    },
    createdAt,
    attempts: 0,
  };
}

describe('encrypted pending mutation storage', () => {
  beforeEach(async () => {
    mockValues.clear();
    mockSecureValues.clear();
    await clearAllPendingMutations();
  });

  test('encrypts native queue at rest and restores it with a device-only key', async () => {
    await writePendingMutations([mutation('user-1')]);

    const stored = mockValues.get('journey.pending-mutations.v3.encrypted');
    expect(stored).toBeTruthy();
    expect(stored).not.toContain('私密苹果');
    expect(mockSecureValues.get('journey.pending-mutations.key.v1')).toBe('test-key');
    await expect(readPendingMutations()).resolves.toHaveLength(1);
  });

  test('drops entries after 24 hours', async () => {
    const old = new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString();
    await writePendingMutations([mutation('user-1', old)]);
    await expect(readPendingMutations()).resolves.toEqual([]);
  });

  test('logout removes only the current user and deletes storage when empty', async () => {
    await writePendingMutations([mutation('user-1'), mutation('user-2')]);
    await clearPendingMutationsForUser('user-1');
    await expect(readPendingMutations()).resolves.toMatchObject([{ ownerUserId: 'user-2' }]);

    await clearPendingMutationsForUser('user-2');
    expect(mockValues.has('journey.pending-mutations.v3.encrypted')).toBe(false);
    expect(mockSecureValues.has('journey.pending-mutations.key.v1')).toBe(false);
  });
});
