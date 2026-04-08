import { useState } from "react";
import { useDidShow } from "@tarojs/taro";
import { getSession } from "../store/session";
import { ROUTES, replaceRoute, relaunchTo } from "./router";

function readSessionSafely() {
  try {
    return getSession();
  } catch (error) {
    console.error("[JourneySessionError]", error);
    return {
      token: "",
      isActivated: false
    };
  }
}

function canRender(mode, session) {
  if (mode === "guest") {
    return !session.token;
  }

  if (!session.token) {
    return false;
  }

  if (mode === "invite") {
    return !session.isActivated;
  }

  return Boolean(session.isActivated);
}

export function usePageGuard(mode = "activated") {
  const [ready, setReady] = useState(() => canRender(mode, readSessionSafely()));

  useDidShow(() => {
    const session = readSessionSafely();

    if (mode === "guest") {
      if (!session.token) {
        setReady(true);
        return;
      }

      setReady(false);

      if (session.isActivated) {
        replaceRoute(ROUTES.home);
        return;
      }

      replaceRoute(ROUTES.invite);
      return;
    }

    if (!session.token) {
      setReady(false);
      relaunchTo(ROUTES.auth);
      return;
    }

    if (mode === "invite") {
      if (session.isActivated) {
        setReady(false);
        replaceRoute(ROUTES.home);
        return;
      }

      setReady(true);
      return;
    }

    if (!session.isActivated) {
      setReady(false);
      replaceRoute(ROUTES.invite);
      return;
    }

    setReady(true);
  });

  return ready;
}
