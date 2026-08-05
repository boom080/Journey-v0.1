import type { ActivityIntensity, MealType } from '@journey/contracts';

import { LOCAL_KNOWLEDGE, LOCAL_KNOWLEDGE_VERSION } from '../content/local-knowledge.ts';

export type MockCandidate =
  | { kind: 'food'; title: string; mealType: MealType; energyKcal: number; explanation: string }
  | { kind: 'activity'; title: string; durationMinutes: number; intensity: ActivityIntensity; energyKcal: number; explanation: string }
  | { kind: 'weight'; weightKg: number; explanation: string }
  | { kind: 'knowledge'; title: string; answer: string; explanation: string };

export function classifyMockInput(input: string): MockCandidate | null {
  const text = input.trim();
  if (!text) return null;
  const weight = text.match(/(?:体重|称了?)\s*(\d{2,3}(?:\.\d)?)/);
  if (weight) return { kind: 'weight', weightKg: Number(weight[1]), explanation: 'Mock 规则识别到体重数值；保存前请确认。' };

  const knowledgeMatch = LOCAL_KNOWLEDGE.find((item) => item.keywords.some((keyword) => text.includes(keyword)));
  if (knowledgeMatch && /(吗|么|如何|怎么|为什么|建议|知识|影响)/.test(text)) {
    return { kind: 'knowledge', title: knowledgeMatch.title, answer: knowledgeMatch.answer, explanation: `来自本机 Journey 常识包 v${LOCAL_KNOWLEDGE_VERSION}；不是模型回答。` };
  }

  if (/(跑|走|游泳|骑车|瑜伽|训练|运动|健身)/.test(text)) {
    const minutes = Number(text.match(/(\d+)\s*(?:分钟|min)/i)?.[1] ?? 30);
    const kcal = Number(text.match(/(\d+)\s*(?:千卡|大卡|kcal)/i)?.[1] ?? Math.max(80, minutes * 6));
    return { kind: 'activity', title: text.slice(0, 40), durationMinutes: minutes, intensity: 'moderate', energyKcal: kcal, explanation: 'Mock 关键词规则识别为运动；热量只是预填值。' };
  }

  if (/(吃|喝|早餐|午餐|晚餐|米饭|面|鸡|蛋|奶|咖啡|水果)/.test(text)) {
    const kcal = Number(text.match(/(\d+)\s*(?:千卡|大卡|kcal)/i)?.[1] ?? 300);
    const hour = new Date().getHours();
    const mealType: MealType = text.includes('早餐')
      ? 'breakfast'
      : text.includes('午餐')
        ? 'lunch'
        : text.includes('晚餐')
          ? 'dinner'
          : text.includes('加餐') || text.includes('夜宵')
            ? 'snack'
            : hour < 10 ? 'breakfast' : hour < 15 ? 'lunch' : hour < 21 ? 'dinner' : 'snack';
    return { kind: 'food', title: text.replace(/^我?(吃了|喝了)/, '').slice(0, 40) || '一份食物', mealType, energyKcal: kcal, explanation: 'Mock 关键词规则识别为饮食；热量只是预填值。' };
  }

  if (knowledgeMatch) return { kind: 'knowledge', title: knowledgeMatch.title, answer: knowledgeMatch.answer, explanation: `来自本机 Journey 常识包 v${LOCAL_KNOWLEDGE_VERSION}；不是模型回答。` };
  return null;
}
