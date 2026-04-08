import { request } from "./request";

export function getMyProfile() {
  return request({
    path: "/profile/me",
    method: "GET",
    authMode: "activated"
  });
}

export function updateMyProfile(data) {
  return request({
    path: "/profile/me",
    method: "PUT",
    data,
    authMode: "activated"
  });
}
