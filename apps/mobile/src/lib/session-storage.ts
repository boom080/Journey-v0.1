import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import type { TokenPair } from '@journey/contracts';

const SESSION_KEY = 'journey.session.v1';

export async function loadStoredSession(): Promise<TokenPair | null> {
  try {
    const value =
      Platform.OS === 'web'
        ? typeof sessionStorage === 'undefined'
          ? null
          : sessionStorage.getItem(SESSION_KEY)
        : await SecureStore.getItemAsync(SESSION_KEY);
    return value ? (JSON.parse(value) as TokenPair) : null;
  } catch {
    return null;
  }
}

export async function saveStoredSession(session: TokenPair): Promise<void> {
  const value = JSON.stringify(session);
  if (Platform.OS === 'web') {
    if (typeof sessionStorage !== 'undefined') sessionStorage.setItem(SESSION_KEY, value);
    return;
  }
  await SecureStore.setItemAsync(SESSION_KEY, value, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

export async function clearStoredSession(): Promise<void> {
  if (Platform.OS === 'web') {
    if (typeof sessionStorage !== 'undefined') sessionStorage.removeItem(SESSION_KEY);
    return;
  }
  await SecureStore.deleteItemAsync(SESSION_KEY);
}
