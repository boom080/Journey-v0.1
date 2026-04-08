import { request } from "./request";

export function getJourneyDays(params = {}) {
  return request({
    path: "/journey-days",
    method: "GET",
    data: params,
    authMode: "activated"
  });
}
