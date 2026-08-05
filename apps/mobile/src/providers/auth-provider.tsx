import { createContext, type PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';

import type { LoginRequest, RegisterRequest, TokenPair } from '@journey/contracts';

import {
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  restoreSession,
  subscribeToSession,
} from '@/lib/api';
import { clearPendingMutationsForUser } from '@/lib/pending-storage';

type AuthContextValue = {
  session: TokenPair | null;
  isLoading: boolean;
  signIn: (payload: LoginRequest) => Promise<void>;
  signUp: (payload: RegisterRequest) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<TokenPair | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = subscribeToSession(setSession);
    void restoreSession().then((value) => {
      setSession(value);
      setIsLoading(false);
    });
    return unsubscribe;
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    session,
    isLoading,
    signIn: async (payload) => { setSession(await loginRequest(payload)); },
    signUp: async (payload) => { setSession(await registerRequest(payload)); },
    signOut: async () => {
      const ownerUserId = session?.user.id;
      await logoutRequest();
      if (ownerUserId) await clearPendingMutationsForUser(ownerUserId);
      setSession(null);
    },
  }), [isLoading, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth 必须在 AuthProvider 内使用');
  return value;
}
