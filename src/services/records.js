import { API_ENDPOINTS } from "../config/runtime";
import { request } from "./request";

export function getFoodRecords(params = {}) {
  return request({
    path: API_ENDPOINTS.records.food,
    method: "GET",
    data: params,
    authMode: "activated"
  });
}

export function createFoodRecord(data) {
  return request({
    path: API_ENDPOINTS.records.food,
    method: "POST",
    data,
    authMode: "activated"
  });
}

export function updateFoodRecord(id, data) {
  return request({
    path: `${API_ENDPOINTS.records.food}/${id}`,
    method: "PUT",
    data,
    authMode: "activated"
  });
}

export function deleteFoodRecord(id) {
  return request({
    path: `${API_ENDPOINTS.records.food}/${id}`,
    method: "DELETE",
    authMode: "activated"
  });
}

export function getActivityRecords(params = {}) {
  return request({
    path: API_ENDPOINTS.records.activity,
    method: "GET",
    data: params,
    authMode: "activated"
  });
}

export function createActivityRecord(data) {
  return request({
    path: API_ENDPOINTS.records.activity,
    method: "POST",
    data,
    authMode: "activated"
  });
}

export function updateActivityRecord(id, data) {
  return request({
    path: `${API_ENDPOINTS.records.activity}/${id}`,
    method: "PUT",
    data,
    authMode: "activated"
  });
}

export function deleteActivityRecord(id) {
  return request({
    path: `${API_ENDPOINTS.records.activity}/${id}`,
    method: "DELETE",
    authMode: "activated"
  });
}
