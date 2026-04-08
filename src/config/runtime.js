export const RUNTIME_CONFIG = {
  apiBaseUrl: String(__API_BASE_URL__ || "http://127.0.0.1:8000").replace(/\/+$/, ""),
  requestTimeout: Number(__REQUEST_TIMEOUT__ || 20000),
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
