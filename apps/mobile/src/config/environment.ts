import { Platform } from 'react-native';

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
  return process.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED?.trim().toLowerCase() !== 'false';
}
