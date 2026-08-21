import { useNetInfo } from '@react-native-community/netinfo';
import { useQueryClient } from '@tanstack/react-query';
import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import type {
  Goal,
  GoalUpsertRequest,
  HomeToday,
  JourneyProfile,
  JourneyResponse,
  ManualRecordKind,
  ManualRecordPayload,
  ProfileUpdateRequest,
} from '@journey/contracts';

import {
  ApiError,
  ApiNetworkError,
  createRecord as createRecordRequest,
  deleteRecord as deleteRecordRequest,
  fetchGoal as fetchGoalRequest,
  fetchHomeToday as fetchHomeTodayRequest,
  fetchJourney as fetchJourneyRequest,
  fetchProfile as fetchProfileRequest,
  saveGoal as saveGoalRequest,
  updateProfile as updateProfileRequest,
  updateRecord as updateRecordRequest,
} from '@/lib/api';
import {
  applyOptimisticMutation,
  activateLocalReplica,
  conflictFields,
  homeFromReplica,
  journeyFromReplica,
  makeLocalRecord,
  mergeServerSnapshot,
  mutateLocalReplica,
  optimisticProfile,
  readLocalReplica,
  removeReplicaRecord,
  type LocalMutation,
  type LocalReplica,
  type ReplicaRecord,
  type ServerReplicaSnapshot,
  type SyncConflict,
  upsertReplicaRecord,
} from '@/lib/local-replica';
import {
  clearPendingMutationsForUser,
  readPendingMutations,
} from '@/lib/pending-storage';
import { useAuth } from '@/providers/auth-provider';

type SyncStatus = 'idle' | 'offline' | 'syncing' | 'error' | 'conflict';

type SyncContextValue = {
  isOnline: boolean;
  pendingCount: number;
  status: SyncStatus;
  conflicts: SyncConflict[];
  fetchProfile: () => Promise<JourneyProfile>;
  fetchGoal: () => Promise<Goal | null>;
  fetchHome: () => Promise<HomeToday>;
  fetchJourney: (limit?: number, cursor?: string, windowDays?: number) => Promise<JourneyResponse>;
  submitRecord: (
    kind: ManualRecordKind,
    payload: ManualRecordPayload,
  ) => Promise<'saved' | 'queued'>;
  updateRecord: (
    kind: ManualRecordKind,
    record: ReplicaRecord,
    payload: Record<string, unknown>,
  ) => Promise<'saved' | 'queued' | 'conflict'>;
  deleteRecord: (
    kind: ManualRecordKind,
    record: ReplicaRecord,
  ) => Promise<'saved' | 'queued' | 'conflict'>;
  saveProfile: (
    current: JourneyProfile,
    payload: ProfileUpdateRequest,
  ) => Promise<'saved' | 'queued' | 'conflict'>;
  saveGoal: (
    current: Goal | null,
    payload: GoalUpsertRequest,
  ) => Promise<'saved' | 'queued' | 'conflict'>;
  retryPending: () => Promise<void>;
  resolveConflict: (conflictId: string, choice: 'local' | 'server') => Promise<void>;
};

const SyncContext = createContext<SyncContextValue | null>(null);

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

function asObject(value: unknown): Record<string, unknown> {
  return value as Record<string, unknown>;
}

function flattenJourney(journey: JourneyResponse): ServerReplicaSnapshot['records'] {
  return journey.items.reduce<ServerReplicaSnapshot['records']>((records, day) => {
    records.food.push(...day.food_records);
    records.activity.push(...day.activity_records);
    records.weight.push(...day.weight_records);
    return records;
  }, { food: [], activity: [], weight: [] });
}

function localCalendarDate(timezone: string, now = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function ninetyDayCutoff(timezone: string): string {
  const [year, month, day] = localCalendarDate(timezone).split('-').map(Number);
  const cutoff = new Date(Date.UTC(year!, month! - 1, day!));
  cutoff.setUTCDate(cutoff.getUTCDate() - 89);
  return cutoff.toISOString().slice(0, 10);
}

async function fetchNinetyDayJourney(timezone: string): Promise<JourneyResponse> {
  const items: JourneyResponse['items'] = [];
  const cutoff = ninetyDayCutoff(timezone);
  let cursor: string | undefined;
  for (let page = 0; page < 3; page += 1) {
    const response = await fetchJourneyRequest(30, cursor);
    items.push(...response.items.filter((day) => day.date >= cutoff));
    const reachedCutoff = response.items.some((day) => day.date < cutoff);
    if (reachedCutoff || !response.has_more || !response.next_cursor) {
      return { items, next_cursor: null, has_more: false };
    }
    cursor = response.next_cursor;
  }
  return { items, next_cursor: cursor ?? null, has_more: Boolean(cursor) };
}

async function fetchGoalOrNull(): Promise<Goal | null> {
  try {
    return await fetchGoalRequest();
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

async function executeMutation(mutation: LocalMutation): Promise<unknown> {
  if (mutation.entity === 'profile') {
    return updateProfileRequest(
      mutation.payload as ProfileUpdateRequest,
      mutation.expectedVersion,
    );
  }
  if (mutation.entity === 'goal') {
    return saveGoalRequest(mutation.payload as GoalUpsertRequest, mutation.expectedVersion);
  }
  if (mutation.operation === 'create') {
    return createRecordRequest(
      mutation.entity,
      mutation.payload as ManualRecordPayload,
      mutation.idempotencyKey,
    );
  }
  if (!mutation.resourceId) throw new Error('待同步变更缺少服务端记录 ID');
  if (mutation.operation === 'update') {
    return updateRecordRequest(
      mutation.entity,
      mutation.resourceId,
      mutation.payload,
      mutation.expectedVersion,
    );
  }
  return deleteRecordRequest(
    mutation.entity,
    mutation.resourceId,
    mutation.expectedVersion,
  );
}

function applyMutationResult(
  replica: LocalReplica,
  mutation: LocalMutation,
  result: unknown,
): void {
  if (mutation.entity === 'profile') {
    replica.profile = result as JourneyProfile;
    return;
  }
  if (mutation.entity === 'goal') {
    replica.goal = result as Goal;
    return;
  }
  if (mutation.operation === 'delete') {
    if (mutation.resourceId) removeReplicaRecord(replica, mutation.entity, mutation.resourceId);
    return;
  }
  upsertReplicaRecord(
    replica,
    mutation.entity,
    result as ReplicaRecord,
    mutation.operation === 'create' ? mutation.resourceId ?? undefined : undefined,
  );
}

function serverConflictDetails(error: ApiError): {
  actualVersion: number;
  server: Record<string, unknown> | null;
} | null {
  if (error.code !== 'sync_conflict' || !error.details || typeof error.details !== 'object') {
    return null;
  }
  const details = error.details as Record<string, unknown>;
  if (typeof details.actual_version !== 'number') return null;
  return {
    actualVersion: details.actual_version,
    server: details.server && typeof details.server === 'object'
      ? details.server as Record<string, unknown>
      : null,
  };
}

function serverMatchesMutation(
  mutation: LocalMutation,
  server: Record<string, unknown> | null,
): boolean {
  return Boolean(server) && Object.entries(mutation.payload).every(
    ([field, value]) => JSON.stringify(server?.[field]) === JSON.stringify(value),
  );
}

function createPayloadFromLocal(
  entity: ManualRecordKind,
  local: Record<string, unknown>,
): Record<string, unknown> {
  const excluded = new Set(['id', 'record_date', 'version', 'created_at', 'updated_at']);
  return Object.fromEntries(
    Object.entries(local).filter(([field]) => !excluded.has(field)),
  );
}

function applyServerConflict(replica: LocalReplica, conflict: SyncConflict): void {
  if (conflict.entity === 'profile') {
    replica.profile = conflict.server as JourneyProfile | null;
    return;
  }
  if (conflict.entity === 'goal') {
    replica.goal = conflict.server as Goal | null;
    return;
  }
  if (conflict.server) {
    upsertReplicaRecord(replica, conflict.entity, conflict.server as ReplicaRecord);
  } else if (conflict.resourceId) {
    removeReplicaRecord(replica, conflict.entity, conflict.resourceId);
  }
}

function localGoal(
  current: Goal | null,
  payload: GoalUpsertRequest,
  localId: string,
  now: string,
): Goal {
  return {
    id: current?.id ?? localId,
    kind: payload.kind,
    target_weight_kg: payload.target_weight_kg ?? null,
    daily_energy_target_kcal: payload.daily_energy_target_kcal ?? null,
    starts_on: payload.starts_on ?? now.slice(0, 10),
    target_date: payload.target_date ?? null,
    is_active: true,
    version: current?.version ?? 0,
    updated_at: now,
  };
}

export function SyncProvider({ children }: PropsWithChildren) {
  const network = useNetInfo();
  const queryClient = useQueryClient();
  const { session } = useAuth();
  const isOnline = network.isConnected !== false;
  const [pendingCount, setPendingCount] = useState(0);
  const [conflicts, setConflicts] = useState<SyncConflict[]>([]);
  const [status, setStatus] = useState<SyncStatus>('idle');

  const publishReplica = useCallback((replica: LocalReplica) => {
    setPendingCount(replica.outbox.length);
    setConflicts(replica.conflicts);
    if (replica.conflicts.length) setStatus('conflict');
    queryClient.setQueryData(['profile'], replica.profile ?? undefined);
    queryClient.setQueryData(['goal'], replica.goal);
    const home = homeFromReplica(replica);
    if (home) queryClient.setQueryData(['home'], home);
  }, [queryClient]);

  const invalidateRecords = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['home'] }),
      queryClient.invalidateQueries({ queryKey: ['journey'] }),
      queryClient.invalidateQueries({ queryKey: ['profile'] }),
      queryClient.invalidateQueries({ queryKey: ['goal'] }),
    ]);
  }, [queryClient]);

  const migrateLegacyQueue = useCallback(async (ownerUserId: string) => {
    const legacy = (await readPendingMutations()).filter(
      (item) => item.ownerUserId === ownerUserId,
    );
    if (!legacy.length) return;
    const replica = await mutateLocalReplica(ownerUserId, (current) => {
      for (const item of legacy) {
        if (current.outbox.some((queued) => queued.idempotencyKey === item.idempotencyKey)) {
          continue;
        }
        const localId = makeId(`local-${item.kind}`);
        const local = makeLocalRecord(item.kind, item.payload, localId);
        const mutation: LocalMutation = {
          id: item.id,
          ownerUserId,
          entity: item.kind,
          operation: 'create',
          resourceId: localId,
          expectedVersion: 0,
          idempotencyKey: item.idempotencyKey,
          payload: asObject(item.payload),
          base: null,
          local: asObject(local),
          createdAt: item.createdAt,
          attempts: item.attempts,
        };
        current.outbox.push(mutation);
        applyOptimisticMutation(current, mutation);
      }
      return current;
    });
    await clearPendingMutationsForUser(ownerUserId);
    publishReplica(replica);
  }, [publishReplica]);

  const pullReplica = useCallback(async (): Promise<LocalReplica> => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    const profile = await fetchProfileRequest();
    const [goal, journey] = await Promise.all([
      fetchGoalOrNull(),
      fetchNinetyDayJourney(profile.timezone),
    ]);
    const snapshot: ServerReplicaSnapshot = {
      profile,
      goal,
      records: flattenJourney(journey),
    };
    const replica = await mutateLocalReplica(
      session.user.id,
      (current) => mergeServerSnapshot(current, snapshot),
    );
    publishReplica(replica);
    return replica;
  }, [publishReplica, session]);

  const pushOutbox = useCallback(async (): Promise<boolean> => {
    if (!session) return false;
    const ownerUserId = session.user.id;
    let replica = await readLocalReplica(ownerUserId);
    const mine = [...replica.outbox];
    for (const mutation of mine) {
      try {
        const result = await executeMutation(mutation);
        replica = await mutateLocalReplica(ownerUserId, (current) => {
          current.outbox = current.outbox.filter((item) => item.id !== mutation.id);
          applyMutationResult(current, mutation, result);
          return current;
        });
      } catch (error) {
        if (error instanceof ApiError) {
          const details = serverConflictDetails(error);
          if (details) {
            if (mutation.operation !== 'delete' &&
                serverMatchesMutation(mutation, details.server)) {
              replica = await mutateLocalReplica(ownerUserId, (current) => {
                current.outbox = current.outbox.filter((item) => item.id !== mutation.id);
                applyMutationResult(current, mutation, details.server);
                return current;
              });
              continue;
            }
            replica = await mutateLocalReplica(ownerUserId, (current) => {
              current.outbox = current.outbox.filter((item) => item.id !== mutation.id);
              const conflict: SyncConflict = {
                id: makeId('conflict'),
                ownerUserId,
                mutation,
                entity: mutation.entity,
                resourceId: mutation.resourceId,
                expectedVersion: mutation.expectedVersion,
                actualVersion: details.actualVersion,
                fields: conflictFields(mutation, details.server),
                local: mutation.local,
                server: details.server,
                createdAt: new Date().toISOString(),
              };
              current.conflicts.push(conflict);
              applyServerConflict(current, conflict);
              return current;
            });
            continue;
          }
          if (mutation.operation === 'delete' && error.status === 404) {
            replica = await mutateLocalReplica(ownerUserId, (current) => {
              current.outbox = current.outbox.filter((item) => item.id !== mutation.id);
              if (mutation.resourceId && mutation.entity !== 'profile' && mutation.entity !== 'goal') {
                removeReplicaRecord(current, mutation.entity, mutation.resourceId);
              }
              return current;
            });
            continue;
          }
          if (mutation.operation === 'update' && error.status === 404 &&
              mutation.entity !== 'profile' && mutation.entity !== 'goal') {
            replica = await mutateLocalReplica(ownerUserId, (current) => {
              current.outbox = current.outbox.filter((item) => item.id !== mutation.id);
              const conflict: SyncConflict = {
                id: makeId('conflict-deleted'),
                ownerUserId,
                mutation,
                entity: mutation.entity,
                resourceId: mutation.resourceId,
                expectedVersion: mutation.expectedVersion,
                actualVersion: 0,
                fields: ['删除状态', ...Object.keys(mutation.payload)],
                local: mutation.local,
                server: null,
                createdAt: new Date().toISOString(),
              };
              current.conflicts.push(conflict);
              applyServerConflict(current, conflict);
              return current;
            });
            continue;
          }
        }
        replica = await mutateLocalReplica(ownerUserId, (current) => {
          current.outbox = current.outbox.map((item) => item.id === mutation.id
            ? { ...item, attempts: item.attempts + 1 }
            : item);
          return current;
        });
        publishReplica(replica);
        return false;
      }
    }
    publishReplica(replica);
    return true;
  }, [publishReplica, session]);

  const retryPending = useCallback(async () => {
    if (!session || !isOnline) {
      setStatus('offline');
      return;
    }
    setStatus('syncing');
    try {
      const pushed = await pushOutbox();
      if (!pushed) {
        setStatus('error');
        return;
      }
      const replica = await pullReplica();
      setStatus(replica.conflicts.length ? 'conflict' : 'idle');
      await invalidateRecords();
    } catch {
      setStatus('error');
    }
  }, [invalidateRecords, isOnline, pullReplica, pushOutbox, session]);

  useEffect(() => {
    let active = true;
    if (!session) {
      void Promise.resolve().then(() => {
        if (!active) return;
        setPendingCount(0);
        setConflicts([]);
        setStatus('idle');
      });
      return () => { active = false; };
    }
    void (async () => {
      activateLocalReplica(session.user.id);
      await migrateLegacyQueue(session.user.id);
      const replica = await readLocalReplica(session.user.id);
      if (!active) return;
      publishReplica(replica);
      if (isOnline) await retryPending();
      else setStatus('offline');
    })();
    return () => { active = false; };
  }, [isOnline, migrateLegacyQueue, publishReplica, retryPending, session]);

  const fetchProfile = useCallback(async () => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    if (isOnline) {
      try {
        const profile = await fetchProfileRequest();
        const replica = await mutateLocalReplica(session.user.id, (current) => ({
          ...current,
          profile,
          lastSyncedAt: new Date().toISOString(),
        }));
        publishReplica(replica);
        return profile;
      } catch (error) {
        if (!(error instanceof ApiNetworkError)) throw error;
      }
    }
    const local = await readLocalReplica(session.user.id);
    if (local.profile) return local.profile;
    throw new ApiNetworkError('本机还没有已同步画像，请联网完成首次同步。');
  }, [isOnline, publishReplica, session]);

  const fetchGoal = useCallback(async () => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    if (isOnline) {
      try {
        const goal = await fetchGoalOrNull();
        const replica = await mutateLocalReplica(session.user.id, (current) => ({
          ...current,
          goal,
          lastSyncedAt: new Date().toISOString(),
        }));
        publishReplica(replica);
        return goal;
      } catch (error) {
        if (!(error instanceof ApiNetworkError)) throw error;
      }
    }
    return (await readLocalReplica(session.user.id)).goal;
  }, [isOnline, publishReplica, session]);

  const fetchHome = useCallback(async () => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    if (isOnline) {
      try {
        return await fetchHomeTodayRequest();
      } catch (error) {
        if (!(error instanceof ApiNetworkError)) throw error;
      }
    }
    const home = homeFromReplica(await readLocalReplica(session.user.id));
    if (home) return home;
    throw new ApiNetworkError('本机还没有已同步记录，请联网完成首次同步。');
  }, [isOnline, session]);

  const fetchJourney = useCallback(async (limit = 7, cursor?: string, windowDays?: number) => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    if (isOnline) {
      try {
        const journey = await fetchJourneyRequest(limit, cursor, windowDays);
        const records = flattenJourney(journey);
        const replica = await mutateLocalReplica(session.user.id, (current) => {
          for (const kind of ['food', 'activity', 'weight'] as const) {
            for (const record of records[kind]) upsertReplicaRecord(current, kind, record);
          }
          current.lastSyncedAt = new Date().toISOString();
          return current;
        });
        publishReplica(replica);
        return journey;
      } catch (error) {
        if (!(error instanceof ApiNetworkError)) throw error;
      }
    }
    return journeyFromReplica(
      await readLocalReplica(session.user.id),
      limit,
      cursor,
      windowDays,
    );
  }, [isOnline, publishReplica, session]);

  const enqueue = useCallback(async (mutation: LocalMutation): Promise<LocalReplica> => {
    const replica = await mutateLocalReplica(mutation.ownerUserId, (current) => {
      current.outbox.push(mutation);
      applyOptimisticMutation(current, mutation);
      return current;
    });
    publishReplica(replica);
    await invalidateRecords();
    return replica;
  }, [invalidateRecords, publishReplica]);

  const outcomeAfterPush = useCallback(async (mutationId: string) => {
    if (!session || !isOnline) return 'queued' as const;
    const pushed = await pushOutbox();
    const current = await readLocalReplica(session.user.id);
    publishReplica(current);
    if (current.conflicts.some((item) => item.mutation.id === mutationId)) {
      return 'conflict' as const;
    }
    return pushed && !current.outbox.some((item) => item.id === mutationId)
      ? 'saved' as const
      : 'queued' as const;
  }, [isOnline, publishReplica, pushOutbox, session]);

  const submitRecord = useCallback(async (
    kind: ManualRecordKind,
    payload: ManualRecordPayload,
  ) => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    const localId = makeId(`local-${kind}`);
    const local = makeLocalRecord(kind, payload, localId);
    const mutation: LocalMutation = {
      id: makeId('mutation'),
      ownerUserId: session.user.id,
      entity: kind,
      operation: 'create',
      resourceId: localId,
      expectedVersion: 0,
      idempotencyKey: makeId('mobile'),
      payload: asObject(payload),
      base: null,
      local: asObject(local),
      createdAt: new Date().toISOString(),
      attempts: 0,
    };
    await enqueue(mutation);
    const outcome = await outcomeAfterPush(mutation.id);
    return outcome === 'saved' ? 'saved' as const : 'queued' as const;
  }, [enqueue, outcomeAfterPush, session]);

  const updateRecord = useCallback(async (
    kind: ManualRecordKind,
    record: ReplicaRecord,
    payload: Record<string, unknown>,
  ) => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    const now = new Date().toISOString();
    const local = {
      ...record,
      ...payload,
      record_date: typeof (payload.measured_at ?? payload.recorded_at) === 'string'
        ? String(payload.measured_at ?? payload.recorded_at).slice(0, 10)
        : record.record_date,
      updated_at: now,
    } as ReplicaRecord;
    const replica = await readLocalReplica(session.user.id);
    const pendingCreate = replica.outbox.find(
      (item) => item.operation === 'create' && item.resourceId === record.id,
    );
    if (pendingCreate) {
      const updated = await mutateLocalReplica(session.user.id, (current) => {
        current.outbox = current.outbox.map((item) => item.id === pendingCreate.id
          ? { ...item, payload: { ...item.payload, ...payload }, local: asObject(local) }
          : item);
        upsertReplicaRecord(current, kind, local);
        return current;
      });
      publishReplica(updated);
      await invalidateRecords();
      return outcomeAfterPush(pendingCreate.id);
    }
    const pendingUpdate = replica.outbox.find(
      (item) => item.operation === 'update' && item.entity === kind &&
        item.resourceId === record.id,
    );
    if (pendingUpdate) {
      const updated = await mutateLocalReplica(session.user.id, (current) => {
        current.outbox = current.outbox.map((item) => item.id === pendingUpdate.id
          ? { ...item, payload: { ...item.payload, ...payload }, local: asObject(local) }
          : item);
        upsertReplicaRecord(current, kind, local);
        return current;
      });
      publishReplica(updated);
      await invalidateRecords();
      return outcomeAfterPush(pendingUpdate.id);
    }
    const mutation: LocalMutation = {
      id: makeId('mutation'),
      ownerUserId: session.user.id,
      entity: kind,
      operation: 'update',
      resourceId: record.id,
      expectedVersion: record.version,
      idempotencyKey: makeId('mobile-update'),
      payload,
      base: asObject(record),
      local: asObject(local),
      createdAt: now,
      attempts: 0,
    };
    await enqueue(mutation);
    return outcomeAfterPush(mutation.id);
  }, [enqueue, invalidateRecords, outcomeAfterPush, publishReplica, session]);

  const deleteRecord = useCallback(async (
    kind: ManualRecordKind,
    record: ReplicaRecord,
  ) => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    const replica = await readLocalReplica(session.user.id);
    const pendingCreate = replica.outbox.find(
      (item) => item.operation === 'create' && item.resourceId === record.id,
    );
    if (pendingCreate) {
      const updated = await mutateLocalReplica(session.user.id, (current) => {
        current.outbox = current.outbox.filter((item) => item.id !== pendingCreate.id);
        removeReplicaRecord(current, kind, record.id);
        return current;
      });
      publishReplica(updated);
      await invalidateRecords();
      return 'saved' as const;
    }
    const pendingUpdate = replica.outbox.find(
      (item) => item.operation === 'update' && item.entity === kind &&
        item.resourceId === record.id,
    );
    if (pendingUpdate) {
      const mutation: LocalMutation = {
        ...pendingUpdate,
        id: makeId('mutation-delete'),
        operation: 'delete',
        payload: {},
        local: null,
        createdAt: new Date().toISOString(),
        attempts: 0,
      };
      const updated = await mutateLocalReplica(session.user.id, (current) => {
        current.outbox = current.outbox.filter((item) => item.id !== pendingUpdate.id);
        current.outbox.push(mutation);
        removeReplicaRecord(current, kind, record.id);
        return current;
      });
      publishReplica(updated);
      await invalidateRecords();
      return outcomeAfterPush(mutation.id);
    }
    const mutation: LocalMutation = {
      id: makeId('mutation'),
      ownerUserId: session.user.id,
      entity: kind,
      operation: 'delete',
      resourceId: record.id,
      expectedVersion: record.version,
      idempotencyKey: makeId('mobile-delete'),
      payload: {},
      base: asObject(record),
      local: null,
      createdAt: new Date().toISOString(),
      attempts: 0,
    };
    await enqueue(mutation);
    return outcomeAfterPush(mutation.id);
  }, [enqueue, invalidateRecords, outcomeAfterPush, publishReplica, session]);

  const saveProfile = useCallback(async (
    current: JourneyProfile,
    payload: ProfileUpdateRequest,
  ) => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    const replica = await readLocalReplica(session.user.id);
    const existing = replica.outbox.find((item) => item.entity === 'profile');
    if (existing) {
      const local = optimisticProfile(existing.local as JourneyProfile, payload);
      const updated = await mutateLocalReplica(session.user.id, (currentReplica) => {
        currentReplica.outbox = currentReplica.outbox.map((item) => item.id === existing.id
          ? {
            ...item,
            payload: { ...item.payload, ...asObject(payload) },
            local: asObject(local),
          }
          : item);
        currentReplica.profile = local;
        return currentReplica;
      });
      publishReplica(updated);
      await invalidateRecords();
      return outcomeAfterPush(existing.id);
    }
    const mutation: LocalMutation = {
      id: makeId('mutation'),
      ownerUserId: session.user.id,
      entity: 'profile',
      operation: 'update',
      resourceId: current.user_id,
      expectedVersion: current.version,
      idempotencyKey: makeId('mobile-profile'),
      payload: asObject(payload),
      base: asObject(current),
      local: asObject(optimisticProfile(current, payload)),
      createdAt: new Date().toISOString(),
      attempts: 0,
    };
    await enqueue(mutation);
    return outcomeAfterPush(mutation.id);
  }, [enqueue, invalidateRecords, outcomeAfterPush, publishReplica, session]);

  const saveGoal = useCallback(async (current: Goal | null, payload: GoalUpsertRequest) => {
    if (!session) throw new Error('登录状态已失效，请重新登录。');
    const now = new Date().toISOString();
    const replica = await readLocalReplica(session.user.id);
    const existing = replica.outbox.find((item) => item.entity === 'goal');
    if (existing) {
      const local = localGoal(existing.local as Goal | null, payload, makeId('local-goal'), now);
      const updated = await mutateLocalReplica(session.user.id, (currentReplica) => {
        currentReplica.outbox = currentReplica.outbox.map((item) => item.id === existing.id
          ? {
            ...item,
            payload: { ...item.payload, ...asObject(payload) },
            local: asObject(local),
          }
          : item);
        currentReplica.goal = local;
        return currentReplica;
      });
      publishReplica(updated);
      await invalidateRecords();
      return outcomeAfterPush(existing.id);
    }
    const localId = current?.id ?? makeId('local-goal');
    const mutation: LocalMutation = {
      id: makeId('mutation'),
      ownerUserId: session.user.id,
      entity: 'goal',
      operation: 'upsert',
      resourceId: current?.id ?? null,
      expectedVersion: current?.version ?? 0,
      idempotencyKey: makeId('mobile-goal'),
      payload: asObject(payload),
      base: current ? asObject(current) : null,
      local: asObject(localGoal(current, payload, localId, now)),
      createdAt: now,
      attempts: 0,
    };
    await enqueue(mutation);
    return outcomeAfterPush(mutation.id);
  }, [enqueue, invalidateRecords, outcomeAfterPush, publishReplica, session]);

  const resolveConflict = useCallback(async (
    conflictId: string,
    choice: 'local' | 'server',
  ) => {
    if (!session) return;
    const ownerUserId = session.user.id;
    const replica = await mutateLocalReplica(ownerUserId, (current) => {
      const conflict = current.conflicts.find((item) => item.id === conflictId);
      if (!conflict) return current;
      current.conflicts = current.conflicts.filter((item) => item.id !== conflictId);
      if (choice === 'server') {
        applyServerConflict(current, conflict);
        return current;
      }
      const rebased: LocalMutation = {
        ...conflict.mutation,
        id: makeId('mutation-rebased'),
        resourceId: typeof conflict.server?.id === 'string'
          ? conflict.server.id
          : conflict.resourceId,
        expectedVersion: conflict.actualVersion,
        base: conflict.server,
        attempts: 0,
        createdAt: new Date().toISOString(),
      };
      if (!conflict.server && conflict.mutation.operation === 'update' &&
          conflict.entity !== 'profile' && conflict.entity !== 'goal' && conflict.local) {
        rebased.operation = 'create';
        rebased.resourceId = conflict.mutation.resourceId;
        rebased.expectedVersion = 0;
        rebased.payload = createPayloadFromLocal(conflict.entity, conflict.local);
      }
      current.outbox.push(rebased);
      applyOptimisticMutation(current, rebased);
      return current;
    });
    publishReplica(replica);
    await invalidateRecords();
    if (isOnline) await retryPending();
  }, [invalidateRecords, isOnline, publishReplica, retryPending, session]);

  const value = useMemo<SyncContextValue>(() => ({
    isOnline,
    pendingCount,
    status: isOnline ? status : 'offline',
    conflicts,
    fetchProfile,
    fetchGoal,
    fetchHome,
    fetchJourney,
    submitRecord,
    updateRecord,
    deleteRecord,
    saveProfile,
    saveGoal,
    retryPending,
    resolveConflict,
  }), [
    conflicts,
    deleteRecord,
    fetchGoal,
    fetchHome,
    fetchJourney,
    fetchProfile,
    isOnline,
    pendingCount,
    resolveConflict,
    retryPending,
    saveGoal,
    saveProfile,
    status,
    submitRecord,
    updateRecord,
  ]);

  return <SyncContext.Provider value={value}>{children}</SyncContext.Provider>;
}

export function useSync(): SyncContextValue {
  const value = useContext(SyncContext);
  if (!value) throw new Error('useSync 必须在 SyncProvider 内使用');
  return value;
}
