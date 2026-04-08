import { API_ENDPOINTS } from "../config/runtime";
import { request } from "./request";

export function getHomeSummary() {
  return request({
    path: API_ENDPOINTS.home.summary,
    method: "GET",
    authMode: "activated"
  });
}
