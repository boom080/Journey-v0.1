import type { ActivityIntensity, GoalKind, MealType } from '@journey/contracts';

export const goalLabels: Record<GoalKind, string> = {
  lose_fat: '减脂',
  gain_muscle: '增肌',
  maintain: '保持状态',
};

export const mealLabels: Record<MealType, string> = {
  breakfast: '早餐',
  lunch: '午餐',
  dinner: '晚餐',
  snack: '加餐',
  other: '其他',
};

export const intensityLabels: Record<ActivityIntensity, string> = {
  low: '轻松',
  moderate: '适中',
  high: '高强度',
};

export function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric', weekday: 'short' })
    .format(new Date(`${value}T00:00:00`));
}

export function formatTime(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

export function formatNumber(value: number, digits = 0) {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(value);
}

export function todayIsoDate() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}
