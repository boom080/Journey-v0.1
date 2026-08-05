import { useNetInfo } from '@react-native-community/netinfo';
import { useQueryClient } from '@tanstack/react-query';
import { createContext, type PropsWithChildren, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import type { ManualRecordKind, ManualRecordPayload, PendingMutation } from '@journey/contracts';

import { ApiNetworkError, createRecord } from '@/lib/api';
import { readPendingMutations, writePendingMutations } from '@/lib/pending-storage';
import { useAuth } from '@/providers/auth-provider';

type SyncStatus = 'idle' | 'offline' | 'syncing' | 'error';

type SyncContextValue = {
  isOnline: boolean;
  pendingCount: number;
  status: SyncStatus;
  submitRecord: (kind: ManualRecordKind, payload: ManualRecordPayload) => Promise<'saved' | 'queued'>;
  retryPending: () => Promise<void>;
};

const SyncContext = createContext<SyncContextValue | null>(null);

function makeId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

export function SyncProvider({ children }: PropsWithChildren) {
  const network = useNetInfo();
  const queryClient = useQueryClient();
  const { session } = useAuth();
  // The API can be reachable on a LAN even when Android's public-internet
  // validation is unavailable. Actual request failures still fall back to the queue.
  const isOnline = network.isConnected !== false;
  const [pendingCount, setPendingCount] = useState(0);
  const [status, setStatus] = useState<SyncStatus>('idle');

  const invalidateRecords = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['home'] }),
      queryClient.invalidateQueries({ queryKey: ['journey'] }),
      queryClient.invalidateQueries({ queryKey: ['profile'] }),
    ]);
  }, [queryClient]);

  const retryPending = useCallback(async () => {
    if (!session || !isOnline) {
      setStatus('offline');
      return;
    }
    const queue = await readPendingMutations();
    const mine = queue.filter((item) => item.ownerUserId === session.user.id);
    if (!mine.length) {
      setPendingCount(0);
      setStatus('idle');
      return;
    }
    setStatus('syncing');
    const remaining: PendingMutation[] = queue.filter((item) => item.ownerUserId !== session.user.id);
    let failedForCurrentUser = 0;
    for (const item of mine) {
      try {
        await createRecord(item.kind, item.payload, item.idempotencyKey);
      } catch {
        remaining.push({ ...item, attempts: item.attempts + 1 });
        failedForCurrentUser += 1;
      }
    }
    await writePendingMutations(remaining);
    setPendingCount(failedForCurrentUser);
    setStatus(failedForCurrentUser ? 'error' : 'idle');
    if (failedForCurrentUser < mine.length) await invalidateRecords();
  }, [invalidateRecords, isOnline, session]);

  useEffect(() => {
    void readPendingMutations().then((queue) => setPendingCount(session ? queue.filter((item) => item.ownerUserId === session.user.id).length : 0));
  }, [session]);

  useEffect(() => {
    if (!session || !isOnline) return;
    const timeout = setTimeout(() => void retryPending(), 0);
    return () => clearTimeout(timeout);
  }, [isOnline, retryPending, session]);

  const submitRecord = useCallback(async (kind: ManualRecordKind, payload: ManualRecordPayload) => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    const mutation: PendingMutation = {
      id: makeId('pending'),
      ownerUserId: session.user.id,
      idempotencyKey: makeId('mobile'),
      kind,
      payload,
      createdAt: new Date().toISOString(),
      attempts: 0,
    };
    if (isOnline) {
      try {
        await createRecord(kind, payload, mutation.idempotencyKey);
        await invalidateRecords();
        return 'saved' as const;
      } catch (error) {
        if (!(error instanceof ApiNetworkError)) throw error;
      }
    }
    const queue = await readPendingMutations();
    queue.push(mutation);
    await writePendingMutations(queue);
    setPendingCount(queue.filter((item) => item.ownerUserId === session.user.id).length);
    setStatus(isOnline ? 'error' : 'offline');
    return 'queued' as const;
  }, [invalidateRecords, isOnline, session]);

  const value = useMemo<SyncContextValue>(() => ({
    isOnline,
    pendingCount,
    status: isOnline ? status : 'offline',
    submitRecord,
    retryPending,
  }), [isOnline, pendingCount, retryPending, status, submitRecord]);

  return <SyncContext.Provider value={value}>{children}</SyncContext.Provider>;
}

export function useSync(): SyncContextValue {
  const value = useContext(SyncContext);
  if (!value) throw new Error('useSync 必须在 SyncProvider 内使用');
  return value;
}
