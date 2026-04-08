import Taro from "@tarojs/taro";

export const CACHE_KEYS = {
  SESSION: "journey.session",
  PROFILE: "journey.profile",
  HOME: "journey.home",
  JOURNEY: "journey.journey"
};

export function getStorage(key, fallback = null) {
  try {
    const value = Taro.getStorageSync(key);
    return value === "" || value === undefined ? fallback : value;
  } catch (error) {
    return fallback;
  }
}

export function setStorage(key, value) {
  Taro.setStorageSync(key, value);
}

export function removeStorage(key) {
  Taro.removeStorageSync(key);
}

export function clearStorage(keys = []) {
  keys.forEach(removeStorage);
}
