import { API_ENDPOINTS } from "../config/runtime";
import { request } from "./request";

function buildJourneyParams(params = {}) {
  const nextParams = {
    ...(params || {})
  };

  if (!nextParams.cursor) {
    delete nextParams.cursor;
  }

  return nextParams;
}

export function getJourneyDays(params = {}) {
  return request({
    path: API_ENDPOINTS.journey.days,
    method: "GET",
    data: buildJourneyParams(params),
    authMode: "activated"
  });
}
