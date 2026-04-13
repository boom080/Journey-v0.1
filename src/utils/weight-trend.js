import { dateOffsetString } from "./day";
import { safeList } from "./day";

const KCAL_PER_KG = 7700;

function toNumber(value) {
  const amount = Number(value || 0);
  return Number.isFinite(amount) ? amount : 0;
}

function parseBalanceText(text) {
  const matched = String(text || "").match(/([+-]?\d+(?:\.\d+)?)\s*kcal/i);
  return matched ? toNumber(matched[1]) : null;
}

function findYesterdayJourneyDay(journey) {
  const yesterday = dateOffsetString(-1);
  const items = safeList(journey?.items);

  return items.find((item) => String(item?.record_date || item?.id || "") === yesterday) || null;
}

export function calculateExpectedWeightChange(balanceKcal) {
  const amount = toNumber(balanceKcal);
  return amount / KCAL_PER_KG;
}

export function getYesterdayWeightTrend(journey) {
  const day = findYesterdayJourneyDay(journey);
  const balanceKcal = day ? parseBalanceText(day.status_text) : null;

  if (balanceKcal === null) {
    return {
      valid: false,
      balance_kcal: null,
      delta_kg: 0
    };
  }

  return {
    valid: true,
    balance_kcal: balanceKcal,
    delta_kg: calculateExpectedWeightChange(balanceKcal)
  };
}

export function formatWeightDelta(deltaKg) {
  const value = toNumber(deltaKg);
  const rounded = Math.round(value * 100) / 100;
  return `${rounded > 0 ? "+" : ""}${rounded.toFixed(2)} kg`;
}
