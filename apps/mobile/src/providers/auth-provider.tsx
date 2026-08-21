import { createContext, type PropsWithChildren, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { LoginRequest, RegisterRequest, TokenPair } from '@journey/contracts';

import {
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  restoreSession,
  subscribeToSession,
} from '@/lib/api';
import { clearPendingMutationsForUser } from '@/lib/pending-storage';
import { purgeLocalReplica } from '@/lib/local-replica';

type AuthContextValue = {
  session: TokenPair | null;
  isLoading: boolean;
  signIn: (payload: LoginRequest) => Promise<void>;
  signUp: (payload: RegisterRequest) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<TokenPair | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const ownerUserIdRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    const unsubscribe = subscribeToSession((value) => {
      const previousOwner = ownerUserIdRef.current;
      const nextOwner = value?.user.id;
      ownerUserIdRef.current = nextOwner;
      setSession(value);
      if (previousOwner && previousOwner !== nextOwner) {
        queryClient.clear();
        void Promise.all([
          clearPendingMutationsForUser(previousOwner),
          purgeLocalReplica(previousOwner),
        ]);
      }
    });
    void restoreSession().then((value) => {
      ownerUserIdRef.current = value?.user.id;
      setSession(value);
      setIsLoading(false);
    });
    return unsubscribe;
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(() => ({
    session,
    isLoading,
    signIn: async (payload) => { setSession(await loginRequest(payload)); },
    signUp: async (payload) => { setSession(await registerRequest(payload)); },
    signOut: async () => {
      const ownerUserId = session?.user.id;
      await logoutRequest();
      if (ownerUserId) {
        await Promise.all([
          clearPendingMutationsForUser(ownerUserId),
          purgeLocalReplica(ownerUserId),
        ]);
      }
      queryClient.clear();
      setSession(null);
    },
  }), [isLoading, queryClient, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth 必须在 AuthProvider 内使用');
  return value;
}
