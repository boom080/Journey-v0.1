import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import type {
  ActivityRecord,
  ActivityRecordCreate,
  FoodRecord,
  FoodRecordCreate,
  Goal,
  HomeToday,
  JourneyDay,
  JourneyProfile,
  JourneyResponse,
  ManualRecordKind,
  ManualRecordPayload,
  ProfileUpdateRequest,
  UUID,
  WeightRecord,
  WeightRecordCreate,
} from '@journey/contracts';

import { estimateRestingEnergy } from '@/lib/energy';

const SCHEMA_VERSION = 1 as const;
const DATA_PREFIX = 'journey.local-replica.v1.encrypted';
const KEY_PREFIX = 'journey.local-replica.key.v1';
const MAX_OUTBOX_MUTATIONS = 1000;

export type ReplicaRecord = FoodRecord | ActivityRecord | WeightRecord;
export type ReplicaEntity = 'profile' | 'goal' | ManualRecordKind;
export type MutationOperation = 'create' | 'update' | 'delete' | 'upsert';

export type LocalMutation = {
  id: string;
  ownerUserId: UUID;
  entity: ReplicaEntity;
  operation: MutationOperation;
  resourceId: string | null;
  expectedVersion: number;
  idempotencyKey: string;
  payload: Record<string, unknown>;
  base: Record<string, unknown> | null;
  local: Record<string, unknown> | null;
  createdAt: string;
  attempts: number;
};

export type SyncConflict = {
  id: string;
  ownerUserId: UUID;
  mutation: LocalMutation;
  entity: ReplicaEntity;
  resourceId: string | null;
  expectedVersion: number;
  actualVersion: number;
  fields: string[];
  local: Record<string, unknown> | null;
  server: Record<string, unknown> | null;
  createdAt: string;
};

export type LocalReplica = {
  schemaVersion: typeof SCHEMA_VERSION;
  ownerUserId: UUID;
  profile: JourneyProfile | null;
  goal: Goal | null;
  records: {
    food: FoodRecord[];
    activity: ActivityRecord[];
    weight: WeightRecord[];
  };
  outbox: LocalMutation[];
  conflicts: SyncConflict[];
  lastSyncedAt: string | null;
};

export type ServerReplicaSnapshot = Pick<LocalReplica, 'profile' | 'goal' | 'records'>;

const webReplicas = new Map<string, LocalReplica>();
const writeLocks = new Map<string, Promise<void>>();
const purgedOwners = new Set<string>();

function ownerSuffix(ownerUserId: UUID): string {
  return ownerUserId.replace(/[^A-Za-z0-9._-]/g, '_');
}

function dataKey(ownerUserId: UUID): string {
  return `${DATA_PREFIX}.${ownerSuffix(ownerUserId)}`;
}

function encryptionKeyName(ownerUserId: UUID): string {
  return `${KEY_PREFIX}.${ownerSuffix(ownerUserId)}`;
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function emptyLocalReplica(ownerUserId: UUID): LocalReplica {
  return {
    schemaVersion: SCHEMA_VERSION,
    ownerUserId,
    profile: null,
    goal: null,
    records: { food: [], activity: [], weight: [] },
    outbox: [],
    conflicts: [],
    lastSyncedAt: null,
  };
}

async function encryptionKey(ownerUserId: UUID): Promise<Crypto.AESEncryptionKey> {
  const name = encryptionKeyName(ownerUserId);
  const stored = await SecureStore.getItemAsync(name);
  if (stored) return Crypto.AESEncryptionKey.import(stored, 'hex');

  const generated = await Crypto.AESEncryptionKey.generate(Crypto.AESKeySize.AES256);
  const encoded = await generated.encoded('hex');
  await SecureStore.setItemAsync(name, encoded, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
  return generated;
}

async function clearNativeReplica(ownerUserId: UUID): Promise<void> {
  await Promise.all([
    AsyncStorage.removeItem(dataKey(ownerUserId)),
    SecureStore.deleteItemAsync(encryptionKeyName(ownerUserId)),
  ]);
}

function validReplica(value: unknown, ownerUserId: UUID): value is LocalReplica {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<LocalReplica>;
  return candidate.schemaVersion === SCHEMA_VERSION &&
    candidate.ownerUserId === ownerUserId &&
    Array.isArray(candidate.outbox) &&
    Array.isArray(candidate.conflicts) &&
    Boolean(candidate.records) &&
    Array.isArray(candidate.records?.food) &&
    Array.isArray(candidate.records?.activity) &&
    Array.isArray(candidate.records?.weight);
}

export async function readLocalReplica(ownerUserId: UUID): Promise<LocalReplica> {
  if (purgedOwners.has(ownerUserId)) return emptyLocalReplica(ownerUserId);
  if (Platform.OS === 'web') {
    return clone(webReplicas.get(ownerUserId) ?? emptyLocalReplica(ownerUserId));
  }

  const encrypted = await AsyncStorage.getItem(dataKey(ownerUserId));
  if (!encrypted) return emptyLocalReplica(ownerUserId);
  try {
    const key = await encryptionKey(ownerUserId);
    const sealed = Crypto.AESSealedData.fromCombined(encrypted);
    const decrypted = await Crypto.aesDecryptAsync(sealed, key, { output: 'bytes' });
    if (typeof decrypted === 'string') throw new Error('Unexpected encrypted replica format');
    const parsed = JSON.parse(new TextDecoder().decode(decrypted)) as unknown;
    if (!validReplica(parsed, ownerUserId)) throw new Error('Invalid replica schema or owner');
    return parsed;
  } catch {
    await clearNativeReplica(ownerUserId);
    return emptyLocalReplica(ownerUserId);
  }
}

export async function writeLocalReplica(replica: LocalReplica): Promise<void> {
  if (purgedOwners.has(replica.ownerUserId)) {
    throw new Error('该账户已退出，拒绝恢复本地健康数据。');
  }
  if (replica.outbox.length > MAX_OUTBOX_MUTATIONS) {
    throw new Error('本机待同步变更已达到 1000 条，请联网同步后继续。');
  }
  if (!validReplica(replica, replica.ownerUserId)) throw new Error('拒绝写入无效本地副本');

  if (Platform.OS === 'web') {
    webReplicas.set(replica.ownerUserId, clone(replica));
    return;
  }
  const key = await encryptionKey(replica.ownerUserId);
  const plaintext = new TextEncoder().encode(JSON.stringify(replica));
  const sealed = await Crypto.aesEncryptAsync(plaintext, key);
  const combined = await sealed.combined('base64');
  await AsyncStorage.setItem(dataKey(replica.ownerUserId), String(combined));
}

export async function mutateLocalReplica(
  ownerUserId: UUID,
  update: (current: LocalReplica) => LocalReplica,
): Promise<LocalReplica> {
  const previous = writeLocks.get(ownerUserId) ?? Promise.resolve();
  let updated = emptyLocalReplica(ownerUserId);
  const operation = previous.catch(() => undefined).then(async () => {
    const current = await readLocalReplica(ownerUserId);
    updated = update(clone(current));
    if (updated.ownerUserId !== ownerUserId) throw new Error('本地副本账户不匹配');
    await writeLocalReplica(updated);
  });
  writeLocks.set(ownerUserId, operation);
  try {
    await operation;
    return clone(updated);
  } finally {
    if (writeLocks.get(ownerUserId) === operation) writeLocks.delete(ownerUserId);
  }
}

export async function purgeLocalReplica(ownerUserId: UUID): Promise<void> {
  purgedOwners.add(ownerUserId);
  await (writeLocks.get(ownerUserId) ?? Promise.resolve()).catch(() => undefined);
  webReplicas.delete(ownerUserId);
  if (Platform.OS !== 'web') await clearNativeReplica(ownerUserId);
  writeLocks.delete(ownerUserId);
}

export function activateLocalReplica(ownerUserId: UUID): void {
  purgedOwners.delete(ownerUserId);
}

function recordTimestamp(kind: ManualRecordKind, record: Record<string, unknown>): string {
  const value = kind === 'weight' ? record.measured_at : record.recorded_at;
  return typeof value === 'string' ? value : new Date().toISOString();
}

function recordDate(kind: ManualRecordKind, record: Record<string, unknown>): string {
  return recordTimestamp(kind, record).slice(0, 10);
}

export function makeLocalRecord(
  kind: ManualRecordKind,
  payload: ManualRecordPayload,
  localId: string,
  now = new Date().toISOString(),
): ReplicaRecord {
  const common = {
    id: localId,
    record_date: recordDate(kind, payload as unknown as Record<string, unknown>),
    source: payload.source ?? 'manual',
    version: 0,
    created_at: now,
    updated_at: now,
  };
  if (kind === 'food') {
    const food = payload as FoodRecordCreate;
    return {
      ...food,
      detail: food.detail ?? null,
      portion_amount: food.portion_amount ?? null,
      portion_unit: food.portion_unit ?? null,
      protein_g: food.protein_g ?? null,
      carbs_g: food.carbs_g ?? null,
      fat_g: food.fat_g ?? null,
      source_ref: food.source_ref ?? null,
      ...common,
    } as FoodRecord;
  }
  if (kind === 'activity') {
    const activity = payload as ActivityRecordCreate;
    return {
      ...activity,
      activity_type: activity.activity_type ?? null,
      note: activity.note ?? null,
      source_ref: activity.source_ref ?? null,
      ...common,
    } as ActivityRecord;
  }
  const weight = payload as WeightRecordCreate;
  return { ...weight, note: weight.note ?? null, ...common } as WeightRecord;
}

export function upsertReplicaRecord(
  replica: LocalReplica,
  kind: ManualRecordKind,
  record: ReplicaRecord,
  replaceId?: string,
): void {
  const records = replica.records[kind] as ReplicaRecord[];
  const targetId = replaceId ?? record.id;
  const index = records.findIndex((item) => item.id === targetId);
  if (index >= 0) records[index] = record;
  else records.push(record);
  records.sort((left, right) => recordTimestamp(kind, right as unknown as Record<string, unknown>)
    .localeCompare(recordTimestamp(kind, left as unknown as Record<string, unknown>)));
}

export function removeReplicaRecord(
  replica: LocalReplica,
  kind: ManualRecordKind,
  recordId: string,
): void {
  replica.records[kind] = replica.records[kind].filter((item) => item.id !== recordId) as never;
}

export function mergeServerSnapshot(
  current: LocalReplica,
  snapshot: ServerReplicaSnapshot,
  syncedAt = new Date().toISOString(),
): LocalReplica {
  const merged: LocalReplica = {
    ...current,
    profile: snapshot.profile,
    goal: snapshot.goal,
    records: clone(snapshot.records),
    lastSyncedAt: syncedAt,
  };
  for (const mutation of current.outbox) applyOptimisticMutation(merged, mutation);
  return merged;
}

export function applyOptimisticMutation(replica: LocalReplica, mutation: LocalMutation): void {
  if (mutation.entity === 'profile') {
    replica.profile = mutation.local as JourneyProfile | null;
    return;
  }
  if (mutation.entity === 'goal') {
    replica.goal = mutation.local as Goal | null;
    return;
  }
  if (mutation.operation === 'delete') {
    if (mutation.resourceId) removeReplicaRecord(replica, mutation.entity, mutation.resourceId);
    return;
  }
  if (mutation.local) {
    upsertReplicaRecord(
      replica,
      mutation.entity,
      mutation.local as ReplicaRecord,
      mutation.resourceId ?? undefined,
    );
  }
}

function dayFromRecords(date: string, replica: LocalReplica): JourneyDay {
  const food = replica.records.food.filter((item) => item.record_date === date);
  const activity = replica.records.activity.filter((item) => item.record_date === date);
  const weight = replica.records.weight.filter((item) => item.record_date === date);
  const intake = food.reduce((total, item) => total + Number(item.energy_kcal), 0);
  const burned = activity.reduce((total, item) => total + Number(item.energy_kcal), 0);
  return {
    date,
    intake_kcal: Math.round(intake * 100) / 100,
    activity_kcal: Math.round(burned * 100) / 100,
    net_kcal: Math.round((intake - burned) * 100) / 100,
    food_records: food,
    activity_records: activity,
    weight_records: weight,
  };
}

export function journeyFromReplica(
  replica: LocalReplica,
  limit: number,
  cursor?: string,
  windowDays?: number,
): JourneyResponse {
  const timezone = replica.profile?.timezone ?? 'UTC';
  const today = localDate(timezone);
  const [year, month, day] = today.split('-').map(Number);
  const cutoffDate = new Date(Date.UTC(year!, month! - 1, day!));
  cutoffDate.setUTCDate(cutoffDate.getUTCDate() - Math.max(0, (windowDays ?? 90) - 1));
  const cutoff = cutoffDate.toISOString().slice(0, 10);
  const dates = Array.from(new Set([
    ...replica.records.food.map((item) => item.record_date),
    ...replica.records.activity.map((item) => item.record_date),
    ...replica.records.weight.map((item) => item.record_date),
  ]))
    .filter((date) => !cursor || date < cursor)
    .filter((date) => !windowDays || date >= cutoff)
    .sort((left, right) => right.localeCompare(left));
  const pageDates = dates.slice(0, limit);
  const hasMore = dates.length > limit;
  return {
    items: pageDates.map((date) => dayFromRecords(date, replica)),
    next_cursor: hasMore ? pageDates.at(-1) ?? null : null,
    has_more: hasMore,
  };
}

function localDate(timezone: string): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

export function homeFromReplica(replica: LocalReplica): HomeToday | null {
  if (!replica.profile) return null;
  const date = localDate(replica.profile.timezone);
  const day = dayFromRecords(date, replica);
  const latestWeight = [...replica.records.weight]
    .sort((left, right) => right.measured_at.localeCompare(left.measured_at))[0];
  const latestWeightKg = latestWeight?.weight_kg ?? replica.profile.latest_weight_kg;
  const restingEnergy = estimateRestingEnergy(replica.profile, latestWeightKg, date);
  return {
    date,
    timezone: replica.profile.timezone,
    intake_kcal: day.intake_kcal,
    activity_kcal: day.activity_kcal,
    net_kcal: day.net_kcal,
    resting_energy: restingEnergy,
    estimated_energy_balance_kcal: restingEnergy.kcal_per_day == null
      ? null
      : Math.round((day.net_kcal - restingEnergy.kcal_per_day) * 100) / 100,
    counts: {
      food: day.food_records.length,
      activity: day.activity_records.length,
      weight: day.weight_records.length,
    },
    latest_weight_kg: latestWeightKg,
    active_goal: replica.goal,
  };
}

export function conflictFields(
  mutation: LocalMutation,
  server: Record<string, unknown> | null,
): string[] {
  if (mutation.operation === 'delete') return ['删除状态'];
  const local = mutation.local ?? mutation.payload;
  const fields = Object.keys(mutation.payload).filter(
    (field) => JSON.stringify(local[field]) !== JSON.stringify(server?.[field]),
  );
  return fields.length ? fields : ['版本'];
}

export function optimisticProfile(
  profile: JourneyProfile,
  payload: ProfileUpdateRequest,
  now = new Date().toISOString(),
): JourneyProfile {
  return { ...profile, ...payload, updated_at: now };
}
