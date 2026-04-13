import Taro from "@tarojs/taro";

export const ROUTES = {
  auth: "/pages/auth/index",
  invite: "/pages/invite/index",
  home: "/pages/home/main",
  journey: "/pages/journey/main",
  profile: "/pages/profile/main",
  food: "/pages/food/main",
  activity: "/pages/activity/main"
};

const TAB_ROUTES = new Set([ROUTES.home, ROUTES.journey, ROUTES.profile]);
const navigationState = {
  key: "",
  promise: null,
  startedAt: 0
};

function normalizeUrl(url = "") {
  return String(url).split("?")[0] || "";
}

function getCurrentRoute() {
  try {
    const pages =
      (typeof Taro.getCurrentPages === "function" && Taro.getCurrentPages()) ||
      (typeof getCurrentPages === "function" ? getCurrentPages() : []);
    const currentPage = pages[pages.length - 1];

    if (!currentPage?.route) {
      return "";
    }

    return currentPage.route.startsWith("/") ? currentPage.route : `/${currentPage.route}`;
  } catch (error) {
    return "";
  }
}

function shouldSkipNavigation(url) {
  const target = normalizeUrl(url);
  const currentRoute = normalizeUrl(getCurrentRoute());
  return Boolean(target && currentRoute && currentRoute === target);
}

function runNavigation(method, url) {
  if (method === "switchTab") {
    return Taro.switchTab({ url });
  }

  if (method === "redirectTo") {
    return Taro.redirectTo({ url });
  }

  if (method === "reLaunch") {
    return Taro.reLaunch({ url });
  }

  return Taro.navigateTo({ url });
}

function navigate(method, url) {
  if (!url || shouldSkipNavigation(url)) {
    return Promise.resolve();
  }

  const key = `${method}:${normalizeUrl(url)}`;
  const now = Date.now();

  if (navigationState.promise && navigationState.key === key && now - navigationState.startedAt < 1200) {
    return navigationState.promise;
  }

  const promise = runNavigation(method, url).finally(() => {
    if (navigationState.promise === promise) {
      navigationState.key = "";
      navigationState.promise = null;
      navigationState.startedAt = 0;
    }
  });

  navigationState.key = key;
  navigationState.promise = promise;
  navigationState.startedAt = now;

  return promise;
}

export function openRoute(url) {
  if (TAB_ROUTES.has(url)) {
    return navigate("switchTab", url);
  }

  return navigate("navigateTo", url);
}

export function replaceRoute(url) {
  if (TAB_ROUTES.has(url)) {
    return navigate("switchTab", url);
  }

  return navigate("redirectTo", url);
}

export function relaunchTo(url) {
  return navigate("reLaunch", url);
}
