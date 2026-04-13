export const API_BASE_URL_ENV_KEY = String(__API_BASE_URL_ENV_KEY__ || "TARO_APP_API_BASE_URL");
export const DEFAULT_API_BASE_URL = String(__DEFAULT_API_BASE_URL__ || "http://127.0.0.1:8000").replace(/\/+$/, "");
export const DEFAULT_REQUEST_TIMEOUT = Number(__DEFAULT_REQUEST_TIMEOUT__ || 10000);

export const RUNTIME_CONFIG = {
  apiBaseUrl: String(__API_BASE_URL__ || DEFAULT_API_BASE_URL).replace(/\/+$/, ""),
  requestTimeout: Number(__REQUEST_TIMEOUT__ || DEFAULT_REQUEST_TIMEOUT),
  featureFlags: {
    aiFoodText: true,
    aiActivityText: true,
    aiHomeSuggestion: true,
    aiFoodImage: false,
    aiActivityOcr: false,
    aiPdf: false,
    aiRag: false
  }
};

export const API_ENDPOINTS = {
  auth: {
    wechatLogin: "/auth/wechat-login",
    verifyInvite: "/auth/verify-invite",
    me: "/auth/me"
  },
  ai: {
    foodTextEstimate: "/ai/food-text-estimate",
    activityTextEstimate: "/ai/activity-text-estimate",
    homeSuggestion: "/ai/home-suggestion"
  },
  home: {
    summary: "/home/summary"
  },
  journey: {
    days: "/journey-days"
  },
  profile: {
    me: "/profile/me"
  },
  records: {
    food: "/food-records",
    activity: "/activity-records"
  }
};
