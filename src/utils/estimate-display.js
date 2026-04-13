import { getFoodDisplayName } from "./food-name";

const FOOD_MEAL_WORDS = [
  { value: "早餐", pattern: /(早餐|早饭|早茶)/ },
  { value: "午餐", pattern: /(午餐|中饭|午饭)/ },
  { value: "晚餐", pattern: /(晚餐|晚饭)/ },
  { value: "加餐", pattern: /(加餐|夜宵|宵夜)/ }
];

const GENERIC_ACTIVITY_TITLES = new Set(["活动", "运动", "训练"]);

function cleanText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .replace(/[，,。；;！!？?]+$/g, "")
    .trim();
}

function stripLeadingPhrases(text, patterns) {
  let nextText = cleanText(text);

  patterns.forEach((pattern) => {
    nextText = nextText.replace(pattern, "");
  });

  return cleanText(nextText);
}

function normalizeMealValue(value) {
  const raw = cleanText(value);
  const matched = FOOD_MEAL_WORDS.find((item) => item.pattern.test(raw));
  return matched?.value || "";
}

function getMealKeyword(text) {
  const raw = cleanText(text);
  const matched = FOOD_MEAL_WORDS.find((item) => item.pattern.test(raw));
  return matched?.value || "";
}

function cleanActivityDraftText(text) {
  return stripLeadingPhrases(cleanText(text), [
    /^(?:我|我刚|我今天|今天|刚刚|刚才|现在|晚上|中午|上午)[，, ]*/i,
    /^(?:做了|进行了|完成了|去做了|安排了|练了)[，, ]*/i
  ]);
}

function pickBetterTitle(primary, fallback, genericTitles) {
  const cleanedPrimary = cleanText(primary);
  const cleanedFallback = cleanText(fallback);

  if (!cleanedFallback) {
    return cleanedPrimary;
  }

  if (!cleanedPrimary) {
    return cleanedFallback;
  }

  if (genericTitles.has(cleanedPrimary) || (cleanedPrimary.length <= 4 && cleanedFallback.length > cleanedPrimary.length + 1)) {
    return cleanedFallback;
  }

  if (cleanedFallback.includes(cleanedPrimary) && cleanedFallback.length > cleanedPrimary.length + 2) {
    return cleanedFallback;
  }

  return cleanedPrimary;
}

export function inferMealFromText(text) {
  return getMealKeyword(text);
}

export function sanitizeFoodEstimateItem(item, draftText = "") {
  const explicitMeal = inferMealFromText(draftText);
  const displayMeal = explicitMeal || normalizeMealValue(item?.meal);
  const displayTitle = getFoodDisplayName(
    {
      ...item,
      meal: displayMeal
    },
    draftText
  );
  const rawDetail = cleanText(item?.detail || item?.title || "");

  return {
    ...item,
    meal: displayMeal,
    detail: rawDetail || displayTitle || "已记录饮食",
    food_name: item?.food_name || displayTitle,
    displayTitle: displayTitle || rawDetail || "已记录饮食",
    displayMeal
  };
}

export function sanitizeActivityEstimateItem(item, draftText = "") {
  const rawTitle = cleanText(item?.name || item?.title || "");
  const cleanedTitle = cleanActivityDraftText(rawTitle);
  const cleanedDraft = cleanActivityDraftText(draftText);
  const displayTitle = pickBetterTitle(cleanedTitle, cleanedDraft, GENERIC_ACTIVITY_TITLES) || rawTitle || cleanedDraft;

  return {
    ...item,
    name: displayTitle || rawTitle || "已记录活动",
    title: displayTitle || rawTitle || "已记录活动",
    displayTitle: displayTitle || rawTitle || "已记录活动"
  };
}

export function formatFoodRecordTitle(record) {
  return getFoodDisplayName(record) || "已记录饮食";
}
