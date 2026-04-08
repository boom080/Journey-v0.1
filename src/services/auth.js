import { API_ENDPOINTS } from "../config/runtime";
import { request } from "./request";

export function wechatLogin(code) {
  return request({
    path: API_ENDPOINTS.auth.wechatLogin,
    method: "POST",
    data: { code },
    authMode: "public",
    timeout: 20000,
    requestName: "微信登录",
    dedupeKey: "auth:wechat-login"
  });
}

export function verifyInvite(inviteCode) {
  return request({
    path: API_ENDPOINTS.auth.verifyInvite,
    method: "POST",
    data: { code: inviteCode },
    authMode: "token",
    timeout: 15000,
    requestName: "邀请码校验"
  });
}
