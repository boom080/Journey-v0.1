import { useRef, useState } from "react";
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

function createGuardState(mode, session) {
  if (mode === "guest") {
    if (!session.token) {
      return {
        ready: true,
        checking: false,
        message: ""
      };
    }

    return {
      ready: false,
      checking: true,
      message: session.isActivated ? "正在直接进入首页..." : "正在继续进入邀请码页...",
      redirectTo: session.isActivated ? ROUTES.home : ROUTES.invite,
      redirectMethod: "relaunch"
    };
  }

  if (!session.token) {
    return {
      ready: false,
      checking: true,
      message: "正在恢复登录状态...",
      redirectTo: ROUTES.auth,
      redirectMethod: "relaunch"
    };
  }

  if (mode === "invite") {
    if (session.isActivated) {
      return {
        ready: false,
        checking: true,
        message: "邀请码已通过，正在进入首页...",
        redirectTo: ROUTES.home,
        redirectMethod: "relaunch"
      };
    }

    return {
      ready: true,
      checking: false,
      message: ""
    };
  }

  if (!session.isActivated) {
    return {
      ready: false,
      checking: true,
      message: "正在继续进入邀请码页...",
      redirectTo: ROUTES.invite,
      redirectMethod: "relaunch"
    };
  }

  return {
    ready: true,
    checking: false,
    message: ""
  };
}

function isSameGuardState(prev, next) {
  return (
    prev.ready === next.ready &&
    prev.checking === next.checking &&
    prev.message === next.message &&
    prev.redirectTo === next.redirectTo &&
    prev.redirectMethod === next.redirectMethod
  );
}

function runGuardRedirect(target, method) {
  if (!target) {
    return Promise.resolve();
  }

  if (method === "relaunch") {
    return relaunchTo(target);
  }

  return replaceRoute(target);
}

export function usePageGuardState(mode = "activated") {
  const redirectRef = useRef("");
  const [state, setState] = useState(() => createGuardState(mode, readSessionSafely()));

  useDidShow(() => {
    const session = readSessionSafely();
    const nextState = createGuardState(mode, session);

    setState((prev) => (isSameGuardState(prev, nextState) ? prev : nextState));

    const redirectKey = nextState.redirectTo ? `${nextState.redirectMethod || "replace"}:${nextState.redirectTo}` : "";

    if (!nextState.redirectTo) {
      redirectRef.current = "";
      return;
    }

    if (redirectRef.current === redirectKey) {
      return;
    }

    redirectRef.current = redirectKey;
    runGuardRedirect(nextState.redirectTo, nextState.redirectMethod);
  });

  return state;
}

export function usePageGuard(mode = "activated") {
  const state = usePageGuardState(mode);
  return state.ready && canRender(mode, readSessionSafely());
}
