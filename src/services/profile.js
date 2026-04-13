import { API_ENDPOINTS } from "../config/runtime";
import { buildProfilePayload, mergeProfileSnapshot, normalizeProfile } from "../utils/profile";
import { request } from "./request";

export async function getMyProfile() {
  const payload = await request({
    path: API_ENDPOINTS.profile.me,
    method: "GET",
    authMode: "activated"
  });

  return normalizeProfile(payload);
}

export async function updateMyProfile(data) {
  const payload = buildProfilePayload(data);
  const response = await request({
    path: API_ENDPOINTS.profile.me,
    method: "PUT",
    data: payload,
    authMode: "activated"
  });

  return mergeProfileSnapshot(payload, response);
}
