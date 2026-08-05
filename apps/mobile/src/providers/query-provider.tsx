import NetInfo from '@react-native-community/netinfo';
import { QueryClient, QueryClientProvider, onlineManager } from '@tanstack/react-query';
import type { PropsWithChildren } from 'react';
import { useEffect, useState } from 'react';

export function JourneyQueryProvider({ children }: PropsWithChildren) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: {
      queries: { staleTime: 30_000, retry: 1, refetchOnReconnect: true },
      mutations: { retry: 0 },
    },
  }));

  useEffect(
    () => onlineManager.setEventListener((setOnline) =>
      NetInfo.addEventListener((state) => setOnline(Boolean(state.isConnected)))),
    [],
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
