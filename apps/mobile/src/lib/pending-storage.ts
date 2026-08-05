import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import type { PendingMutation } from '@journey/contracts';

const QUEUE_KEY = 'journey.pending-mutations.v3.encrypted';
const LEGACY_QUEUE_KEY = 'journey.pending-mutations.v2';
const ENCRYPTION_KEY = 'journey.pending-mutations.key.v1';
const RETENTION_MS = 24 * 60 * 60 * 1000;
const MAX_PENDING_MUTATIONS = 50;

let webQueue: PendingMutation[] = [];

function retained(queue: PendingMutation[], now = Date.now()): PendingMutation[] {
  return queue
    .filter((item) => {
      const createdAt = new Date(item.createdAt).getTime();
      return Number.isFinite(createdAt) && now - createdAt <= RETENTION_MS;
    })
    .slice(-MAX_PENDING_MUTATIONS);
}

async function encryptionKey(): Promise<Crypto.AESEncryptionKey> {
  const stored = await SecureStore.getItemAsync(ENCRYPTION_KEY);
  if (stored) return Crypto.AESEncryptionKey.import(stored, 'hex');

  const generated = await Crypto.AESEncryptionKey.generate(Crypto.AESKeySize.AES256);
  const encoded = await generated.encoded('hex');
  await SecureStore.setItemAsync(ENCRYPTION_KEY, encoded, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
  return generated;
}

async function clearNativeStorage(): Promise<void> {
  await Promise.all([
    AsyncStorage.removeItem(QUEUE_KEY),
    AsyncStorage.removeItem(LEGACY_QUEUE_KEY),
    SecureStore.deleteItemAsync(ENCRYPTION_KEY),
  ]);
}

export async function readPendingMutations(now = Date.now()): Promise<PendingMutation[]> {
  if (Platform.OS === 'web') return retained(webQueue, now);

  await AsyncStorage.removeItem(LEGACY_QUEUE_KEY);
  const encrypted = await AsyncStorage.getItem(QUEUE_KEY);
  if (!encrypted) return [];

  try {
    const key = await encryptionKey();
    const sealed = Crypto.AESSealedData.fromCombined(encrypted);
    const decrypted = await Crypto.aesDecryptAsync(sealed, key, { output: 'bytes' });
    if (typeof decrypted === 'string') throw new Error('Unexpected encrypted queue format');
    const parsed = JSON.parse(new TextDecoder().decode(decrypted)) as PendingMutation[];
    const active = retained(parsed, now);
    if (active.length !== parsed.length) await writePendingMutations(active);
    return active;
  } catch {
    await clearNativeStorage();
    return [];
  }
}

export async function writePendingMutations(queue: PendingMutation[]): Promise<void> {
  const active = retained(queue);
  if (Platform.OS === 'web') {
    webQueue = active;
    return;
  }

  await AsyncStorage.removeItem(LEGACY_QUEUE_KEY);
  if (!active.length) {
    await clearNativeStorage();
    return;
  }

  const key = await encryptionKey();
  const plaintext = new TextEncoder().encode(JSON.stringify(active));
  const sealed = await Crypto.aesEncryptAsync(plaintext, key);
  const combined = await sealed.combined('base64');
  await AsyncStorage.setItem(QUEUE_KEY, String(combined));
}

export async function clearPendingMutationsForUser(ownerUserId: string): Promise<void> {
  const queue = await readPendingMutations();
  await writePendingMutations(queue.filter((item) => item.ownerUserId !== ownerUserId));
}

export async function clearAllPendingMutations(): Promise<void> {
  webQueue = [];
  if (Platform.OS !== 'web') await clearNativeStorage();
}
