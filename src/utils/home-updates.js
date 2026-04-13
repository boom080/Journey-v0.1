import { safeList } from "./day";
import { getFoodDisplayName } from "./food-name";

const MEAL_WORDS = new Set(["早餐", "午餐", "晚餐", "加餐", "夜宵"]);

function cleanText(value) {
  if (value === null || value === undefined) {
    return "";
  }

  return String(value).trim();
}

function looksLikeMeal(value) {
  return MEAL_WORDS.has(cleanText(value));
}

function getKcalNumber(value) {
  const matched = String(value || "").match(/([+-]?\d+(?:\.\d+)?)/);
  return matched ? Number(matched[1]) : 0;
}

function isFoodLikeUpdate(item = {}) {
  if (item.kind === "food" || item.type === "food") {
    return true;
  }

  if (cleanText(item.meal) || cleanText(item.detail) || cleanText(item.food_name) || cleanText(item.foodTitle)) {
    return true;
  }

  if (looksLikeMeal(item.title)) {
    return true;
  }

  return getKcalNumber(item.kcal) >= 0 && !cleanText(item.name);
}

function pickFirstText(values) {
  return values.map(cleanText).find(Boolean) || "";
}

function getFoodUpdateTitle(item = {}) {
  const title = cleanText(item.title);
  const description = cleanText(item.description);
  const displayName = getFoodDisplayName(
    {
      ...item,
      detail: item.detail || description,
      title: looksLikeMeal(title) ? "" : title
    },
    description
  );

  return (
    displayName ||
    pickFirstText([
      item.detail,
      item.content,
      item.food_name,
      item.foodTitle,
      looksLikeMeal(title) ? "" : title,
      description
    ]) ||
    "已记录饮食"
  );
}

function getActivityUpdateTitle(item = {}) {
  return (
    pickFirstText([
      item.name,
      item.activity_name,
      item.content,
      item.title,
      item.description
    ]) || "已记录活动"
  );
}

export function getUpdatePrimaryTitle(item = {}) {
  return isFoodLikeUpdate(item) ? getFoodUpdateTitle(item) : getActivityUpdateTitle(item);
}

export function normalizeHomeUpdate(item = {}) {
  return {
    ...item,
    title: getUpdatePrimaryTitle(item)
  };
}

export function normalizeHomeUpdates(items = []) {
  return safeList(items).map(normalizeHomeUpdate);
}
