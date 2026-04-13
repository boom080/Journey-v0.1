import { API_ENDPOINTS } from "../config/runtime";
import { applyDailyEnergyToSummary } from "../utils/daily-energy";
import { buildHomeSummaryText } from "../utils/home-copy";
import { normalizeHomeUpdates } from "../utils/home-updates";
import { getCachedProfile, saveCachedHome } from "../store/session";
import { request } from "./request";

export function getHomeSummary() {
  return request({
    path: API_ENDPOINTS.home.summary,
    method: "GET",
    authMode: "activated"
  });
}

export function buildHomeSummary(payload, profile) {
  const summary = applyDailyEnergyToSummary(
    {
      ...(payload || {}),
      extra: payload?.extra || {}
    },
    profile
  );

  return {
    ...summary,
    recent_updates: normalizeHomeUpdates(summary.recent_updates),
    today_summary: buildHomeSummaryText(summary),
    extra: {
      ...(summary.extra || {}),
      original_today_summary: payload?.today_summary || ""
    }
  };
}

export async function refreshHomeCache(profile = getCachedProfile()) {
  const payload = await getHomeSummary();
  const summary = buildHomeSummary(payload, profile);
  saveCachedHome(summary);
  return summary;
}
