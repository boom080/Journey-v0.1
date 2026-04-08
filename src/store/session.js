import { CACHE_KEYS, clearStorage, getStorage, setStorage } from "./cache";

const defaultSession = {
  token: "",
  user: null,
  isActivated: false,
  inviteCodeId: ""
};

export function getSession() {
  return {
    ...defaultSession,
    ...(getStorage(CACHE_KEYS.SESSION, {}) || {})
  };
}

export function saveSession(nextSession) {
  const merged = {
    ...getSession(),
    ...(nextSession || {})
  };

  setStorage(CACHE_KEYS.SESSION, merged);
  return merged;
}

export function getCachedProfile() {
  return getStorage(CACHE_KEYS.PROFILE, null);
}

export function saveCachedProfile(profile) {
  setStorage(CACHE_KEYS.PROFILE, profile);
}

export function getCachedHome() {
  return getStorage(CACHE_KEYS.HOME, null);
}

export function saveCachedHome(data) {
  setStorage(CACHE_KEYS.HOME, data);
}

export function getCachedJourney() {
  return (
    getStorage(CACHE_KEYS.JOURNEY, {
      items: [],
      nextCursor: "",
      hasMore: true
    }) || {
      items: [],
      nextCursor: "",
      hasMore: true
    }
  );
}

export function saveCachedJourney(data) {
  setStorage(CACHE_KEYS.JOURNEY, data);
}

export function invalidateTimelineCaches() {
  clearStorage([CACHE_KEYS.HOME, CACHE_KEYS.JOURNEY]);
}

export function clearAllSessionData() {
  clearStorage([
    CACHE_KEYS.SESSION,
    CACHE_KEYS.PROFILE,
    CACHE_KEYS.HOME,
    CACHE_KEYS.JOURNEY
  ]);
}
