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

export function openRoute(url) {
  if (TAB_ROUTES.has(url)) {
    return Taro.switchTab({ url });
  }

  return Taro.navigateTo({ url });
}

export function replaceRoute(url) {
  if (TAB_ROUTES.has(url)) {
    return Taro.switchTab({ url });
  }

  return Taro.redirectTo({ url });
}

export function relaunchTo(url) {
  return Taro.reLaunch({ url });
}
