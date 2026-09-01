import Constants from 'expo-constants';
import { Platform } from 'react-native';

export type LocalTestAccount = {
  identifier: string;
  password: string;
};

type RuntimeExtra = {
  appVariant?: string;
  capabilities?: {
    foodImageAnalysis?: boolean;
    localTestAccount?: boolean;
    agentDebugDetails?: boolean;
  };
  localTestAccount?: LocalTestAccount | null;
};

const platformDefault = Platform.select({
  android: 'http://10.0.2.2:8000',
  default: 'http://127.0.0.1:8000',
});

export function getApiBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  const value = configured || platformDefault;

  if (!value) {
    throw new Error('缺少 EXPO_PUBLIC_API_BASE_URL');
  }

  try {
    return new URL(value).toString().replace(/\/$/, '');
  } catch {
    throw new Error('EXPO_PUBLIC_API_BASE_URL 必须是有效 URL');
  }
}

export function isFoodImageAnalysisEnabled(): boolean {
  const extra = Constants.expoConfig?.extra as RuntimeExtra | undefined;
  return extra?.appVariant === 'development' && extra.capabilities?.foodImageAnalysis === true;
}

export function isAgentDebugDetailsEnabled(): boolean {
  const extra = Constants.expoConfig?.extra as RuntimeExtra | undefined;
  return extra?.appVariant === 'development' && extra.capabilities?.agentDebugDetails === true;
}

export function getLocalTestAccount(): LocalTestAccount | null {
  const extra = Constants.expoConfig?.extra as RuntimeExtra | undefined;
  const account = extra?.localTestAccount;
  if (
    extra?.appVariant !== 'development' ||
    extra.capabilities?.localTestAccount !== true ||
    !account?.identifier.trim() ||
    !account.password
  ) {
    return null;
  }
  return { identifier: account.identifier.trim(), password: account.password };
}
