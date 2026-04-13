import { currentTimeString, todayString } from "./day";
import { getFoodDisplayName } from "./food-name";

export function createEmptyAiResult(aiType) {
  return {
    capability: aiType,
    provider: "",
    model: "",
    source_type: "ai",
    ai_type: aiType,
    items: [],
    total_kcal: 0,
    summary: "",
    extra: {}
  };
}

export function createAiState(aiType) {
  return {
    input: "",
    loading: false,
    confirming: false,
    error: "",
    result: createEmptyAiResult(aiType)
  };
}

export function normalizeAiResult(payload, aiType) {
  return {
    ...createEmptyAiResult(aiType),
    ...(payload || {}),
    items: Array.isArray(payload?.items) ? payload.items : [],
    extra: payload?.extra || {}
  };
}

export function buildFoodRecordFromAi(item, defaults = {}) {
  const normalizedFoodName = getFoodDisplayName(item, defaults.detail || "");

  return {
    record_date: item.record_date || defaults.record_date || todayString(),
    time_text: item.time_text || defaults.time_text || currentTimeString(),
    meal: item.meal || defaults.meal || "加餐",
    detail: normalizedFoodName || item.detail || item.title || defaults.detail || "AI 饮食估算",
    location: item.location || defaults.location || "",
    kcal: Number(item.kcal || defaults.kcal || 0),
    source_type: item.source_type || "ai",
    ai_type: item.ai_type || defaults.ai_type || "food_text_estimate"
  };
}

export function buildActivityRecordFromAi(item, defaults = {}) {
  return {
    record_date: item.record_date || defaults.record_date || todayString(),
    time_text: item.time_text || defaults.time_text || currentTimeString(),
    name: item.name || item.title || defaults.name || "AI 活动估算",
    location: item.location || defaults.location || "",
    kcal: Number(item.kcal || defaults.kcal || 0),
    source_type: item.source_type || "ai",
    ai_type: item.ai_type || defaults.ai_type || "activity_text_estimate"
  };
}
