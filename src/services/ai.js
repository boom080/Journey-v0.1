import { API_ENDPOINTS } from "../config/runtime";
import { request } from "./request";

export function estimateFoodText(data) {
  return request({
    path: API_ENDPOINTS.ai.foodTextEstimate,
    method: "POST",
    data,
    authMode: "activated",
    timeout: 20000,
    requestName: "饮食一句话估算"
  });
}

export function estimateActivityText(data) {
  return request({
    path: API_ENDPOINTS.ai.activityTextEstimate,
    method: "POST",
    data,
    authMode: "activated",
    timeout: 20000,
    requestName: "活动一句话估算"
  });
}

export function generateHomeSuggestion(data = {}) {
  return request({
    path: API_ENDPOINTS.ai.homeSuggestion,
    method: "POST",
    data,
    authMode: "activated",
    timeout: 20000,
    requestName: "首页建议生成"
  });
}
