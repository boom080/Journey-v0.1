import Taro from "@tarojs/taro";
import { RUNTIME_CONFIG } from "../config/runtime";
import { clearAllSessionData, getSession } from "../store/session";
import { ROUTES, relaunchTo, replaceRoute } from "../utils/router";

export class AppRequestError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = "AppRequestError";
    this.code = options.code || "REQUEST_ERROR";
    this.statusCode = options.statusCode || 0;
    this.redirectTo = options.redirectTo || "";
    this.extra = options.extra || {};
  }
}

export const API_BASE_URL = RUNTIME_CONFIG.apiBaseUrl;
export const REQUEST_TIMEOUT = RUNTIME_CONFIG.requestTimeout;
const pendingRequestMap = new Map();

function normalizePath(path) {
  return path.startsWith("/") ? path : `/${path}`;
}

function isLoopbackBaseUrl(url) {
  return /127\.0\.0\.1|localhost/.test(url);
}

function getNetworkHint() {
  if (isLoopbackBaseUrl(API_BASE_URL)) {
    return "如果你在真机或远程调试环境，请把 127.0.0.1 改成电脑局域网 IP。";
  }

  return "";
}

function createRequestError(message, options = {}) {
  return new AppRequestError(message, options);
}

function handleAuthRedirect(statusCode) {
  if (statusCode === 401) {
    clearAllSessionData();
    relaunchTo(ROUTES.auth);
    return ROUTES.auth;
  }

  if (statusCode === 403) {
    replaceRoute(ROUTES.invite);
    return ROUTES.invite;
  }

  return "";
}

function buildRequestKey({ method, path, data, authMode, dedupeKey }) {
  if (dedupeKey) {
    return dedupeKey;
  }

  return JSON.stringify({
    method,
    path,
    data: data || null,
    authMode
  });
}

export async function request({
  path,
  method = "GET",
  data,
  authMode = "activated",
  timeout = REQUEST_TIMEOUT,
  headers = {},
  requestName = "",
  dedupeKey = ""
}) {
  const session = getSession();

  if (authMode !== "public" && !session.token) {
    relaunchTo(ROUTES.auth);
    throw createRequestError("请先完成微信登录", {
      code: "AUTH_REQUIRED",
      redirectTo: ROUTES.auth
    });
  }

  if (authMode === "activated" && !session.isActivated) {
    replaceRoute(ROUTES.invite);
    throw createRequestError("邀请码通过后才能继续使用", {
      code: "INVITE_REQUIRED",
      redirectTo: ROUTES.invite
    });
  }

  const requestKey = buildRequestKey({ method, path, data, authMode, dedupeKey });
  if (pendingRequestMap.has(requestKey)) {
    return pendingRequestMap.get(requestKey);
  }

  const requestPromise = (async () => {
    let response;

    try {
      response = await Taro.request({
        url: `${API_BASE_URL}${normalizePath(path)}`,
        method,
        data,
        timeout,
        header: {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...(session.token ? { Authorization: `Bearer ${session.token}` } : {}),
          ...headers
        }
      });
    } catch (error) {
      const message = String(error?.errMsg || error?.message || "");
      const requestLabel = requestName || normalizePath(path);

      if (message.includes("timeout")) {
        throw createRequestError(
          `${requestLabel} 请求超时，请确认后端已启动且 ${API_BASE_URL} 可以访问。${getNetworkHint()}`.trim(),
          {
            code: "NETWORK_TIMEOUT"
          }
        );
      }

      if (message.includes("fail")) {
        throw createRequestError(
          `${requestLabel} 无法连接到服务，请确认后端地址 ${API_BASE_URL} 正确且后端已启动。${getNetworkHint()}`.trim(),
          {
            code: "NETWORK_UNREACHABLE"
          }
        );
      }

      throw createRequestError(message || "请求失败", {
        code: "NETWORK_UNKNOWN"
      });
    }

    const payload = response.data || {};
    const ok = response.statusCode >= 200 && response.statusCode < 300;

    if (!ok) {
      const redirectTo = handleAuthRedirect(response.statusCode);

      throw createRequestError(payload.detail || payload.message || "请求失败", {
        code: "HTTP_ERROR",
        statusCode: response.statusCode,
        redirectTo,
        extra: payload
      });
    }

    return payload;
  })();

  pendingRequestMap.set(requestKey, requestPromise);

  try {
    return await requestPromise;
  } finally {
    pendingRequestMap.delete(requestKey);
  }
}
