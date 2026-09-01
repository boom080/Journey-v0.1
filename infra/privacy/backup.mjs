#!/usr/bin/env node
// Bounded local/Compose backup tooling. No arbitrary live restore or promotion.
import { createCipheriv, createDecipheriv, createHash, randomBytes, randomUUID } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const FORMAT = 'journey-private-backup-1';
const MAX_BYTES = 64 * 1024 * 1024;
const EPHEMERAL = ['agent_runs', 'agent_tool_runs', 'agent_confirmations', 'agent_threads', 'agent_consents', 'auth_sessions', 'idempotency_keys'];
const PROTECTED = ['users', 'identities', 'password_credentials', 'profiles', 'goals', 'food_records', 'activity_records', 'weight_records', 'life_inspirations'];

function docker(args, input) {
  const result = spawnSync('docker', args, { input, maxBuffer: MAX_BYTES, timeout: 60_000 });
  if (result.error || result.status !== 0) {
    // Driver output can include data/credentials: only expose the safe operation.
    throw new Error(`Docker ${args[0]} failed; inspect the isolated operation securely`);
  }
  return result.stdout;
}

function privateDirectory(directory) {
  if (!path.isAbsolute(directory) || directory === REPO || directory === path.parse(directory).root) throw new Error('Choose a specific absolute private directory');
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const stat = fs.lstatSync(directory);
  if (!stat.isDirectory() || stat.isSymbolicLink() || (stat.mode & 0o077)) throw new Error('Directory must be private (0700), not a symlink');
}

function keyAt(filename) {
  const stat = fs.lstatSync(filename);
  if (!stat.isFile() || stat.isSymbolicLink() || (stat.mode & 0o077) || stat.size !== 32) throw new Error('Key must be a private regular 32-byte file (0600)');
  return fs.readFileSync(filename);
}

export function seal(plain, key, metadata) {
  const iv = randomBytes(12);
  const cipher = createCipheriv('aes-256-gcm', key, iv);
  cipher.setAAD(Buffer.from(JSON.stringify(metadata)));
  const encrypted = Buffer.concat([cipher.update(plain), cipher.final()]);
  return Buffer.from(JSON.stringify({ format: FORMAT, metadata, iv: iv.toString('base64'), tag: cipher.getAuthTag().toString('base64'), data: encrypted.toString('base64') }));
}

export function unseal(envelope, key, { allowExpired = false, now = new Date() } = {}) {
  if (envelope.length > MAX_BYTES) throw new Error('Archive exceeds the bounded restore limit');
  const item = JSON.parse(envelope.toString());
  if (item.format !== FORMAT) throw new Error('Not a managed Journey backup');
  const decipher = createDecipheriv('aes-256-gcm', key, Buffer.from(item.iv, 'base64'));
  decipher.setAAD(Buffer.from(JSON.stringify(item.metadata)));
  decipher.setAuthTag(Buffer.from(item.tag, 'base64'));
  const plain = Buffer.concat([decipher.update(Buffer.from(item.data, 'base64')), decipher.final()]);
  const created = Date.parse(item.metadata.created_at);
  const expires = Date.parse(item.metadata.expires_at);
  if (!Number.isFinite(created) || !Number.isFinite(expires) || expires <= created || expires - created > 7 * 86400_000) throw new Error('Invalid backup retention window');
  if (!allowExpired && expires <= now.getTime()) throw new Error('Backup expired; restore refused');
  if (createHash('sha256').update(plain).digest('hex') !== item.metadata.dump_sha256) throw new Error('Dump digest mismatch');
  return { plain, metadata: item.metadata };
}

function source(container, project) {
  if (!/^[a-z0-9][a-z0-9_-]+$/.test(container) || !/^journey(?:-[a-z0-9-]+)?$/.test(project)) throw new Error('Explicit Journey container and project required');
  const [item] = JSON.parse(docker(['inspect', container]));
  const labels = item.Config.Labels ?? {};
  if (labels['com.docker.compose.project'] !== project || labels['com.docker.compose.project.working_dir'] !== REPO || !['db', 'test-db'].includes(labels['com.docker.compose.service'])) throw new Error('Container is not this workspace\'s Journey database');
  return item;
}

function pg(container, database, user, sql) {
  return docker(['exec', '-i', container, 'psql', '-X', '-qAt', '-v', 'ON_ERROR_STOP=1', '-U', user, '-d', database], sql).toString().trim();
}

function snapshots(container, database, user) {
  const result = {};
  for (const table of PROTECTED) {
    const sql = `SELECT json_build_object('rows',count(*),'digest',md5(COALESCE(string_agg(row_to_json(t)::text,'' ORDER BY row_to_json(t)::text),''))) FROM public.${table} t;`;
    result[table] = JSON.parse(pg(container, database, user, sql));
  }
  return result;
}

export function scrubSQL() {
  return fs.readFileSync(path.join(REPO, 'infra/privacy/scrub-restored-agent.sql'));
}

export function backup({ container, project, database, user, directory, keyFile, includeAgentState = false, retentionDays = 7 }) {
  source(container, project);
  if (!/^[a-zA-Z0-9_]+$/.test(database) || !/^[a-zA-Z0-9_]+$/.test(user)) throw new Error('Invalid database/user name');
  if (!Number.isInteger(retentionDays) || retentionDays < 1 || retentionDays > 7) throw new Error('Backup retention must be 1..7 days');
  privateDirectory(directory);
  if (path.dirname(path.resolve(keyFile)) === path.resolve(directory)) throw new Error('Store the key separately from archives');
  const key = keyAt(keyFile);
  const excludes = includeAgentState ? [] : EPHEMERAL.map(table => `--exclude-table-data=public.${table}`);
  const plain = docker(['exec', container, 'pg_dump', '-U', user, '-d', database, '--format=custom', '--no-owner', '--no-acl', ...excludes]);
  const now = new Date();
  const metadata = { project, database, created_at: now.toISOString(), expires_at: new Date(now.getTime() + retentionDays * 86400_000).toISOString(), mode: includeAgentState ? 'encrypted-migration-rollback' : 'ephemeral-agent-excluded', dump_sha256: createHash('sha256').update(plain).digest('hex') };
  const encoded = seal(plain, key, metadata);
  if (encoded.length > MAX_BYTES) throw new Error('Encrypted archive exceeds 64 MiB; use a reviewed large-database workflow');
  const filename = path.join(directory, `journey-${randomUUID()}.jbackup`);
  fs.writeFileSync(filename, encoded, { mode: 0o600, flag: 'wx' });
  unseal(fs.readFileSync(filename), key); // Authenticated read-back before reporting success.
  return { archive: filename, bytes: encoded.length, ...metadata };
}

export function prunePlan(directory, keyFile, now = new Date()) {
  privateDirectory(directory);
  const key = keyAt(keyFile);
  const expired = [];
  for (const filename of fs.readdirSync(directory)) {
    if (!/^journey-[a-f0-9-]{36}\.jbackup$/.test(filename)) continue;
    const full = path.join(directory, filename);
    const stat = fs.lstatSync(full);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > MAX_BYTES) continue;
    // An invalid/tag-mismatched file stops the operation, not an excuse to delete it.
    const { metadata } = unseal(fs.readFileSync(full), key, { allowExpired: true });
    if (Date.parse(metadata.expires_at) <= now.getTime()) expired.push({ path: full, bytes: stat.size, sha256: createHash('sha256').update(fs.readFileSync(full)).digest('hex') });
  }
  return expired;
}

export function pruneExpired(directory, keyFile, { apply = false, confirm, now = new Date() } = {}) {
  const expired = prunePlan(directory, keyFile, now);
  if (apply) {
    if (confirm !== 'delete-expired-journey-backups') throw new Error('Explicit expired-backup deletion confirmation required');
    for (const item of expired) {
      const stat = fs.lstatSync(item.path);
      if (!stat.isFile() || stat.isSymbolicLink() || stat.size !== item.bytes || createHash('sha256').update(fs.readFileSync(item.path)).digest('hex') !== item.sha256) throw new Error('Backup changed after inspection; deletion refused');
    }
    for (const item of expired) fs.unlinkSync(item.path);
  }
  return { dry_run: !apply, expired, removed: apply ? expired.length : 0 };
}

export async function drill({ archive, keyFile, report }) {
  const { plain, metadata } = unseal(fs.readFileSync(archive), keyAt(keyFile));
  const container = `journey-privacy-restore-${randomUUID().slice(0, 12)}`;
  let created = false;
  let result;
  try {
    docker(['run', '--detach', '--name', container, '--network', 'none', '--tmpfs', '/var/lib/postgresql', '--label', 'journey.privacy.restore=isolated', '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', '-e', 'POSTGRES_USER=journey', '-e', 'POSTGRES_DB=journey_restore', 'postgres:18.4-alpine']);
    created = true;
    let ready = false;
    for (let attempt = 0; attempt < 40; attempt += 1) {
      try { docker(['exec', container, 'pg_isready', '-U', 'journey', '-d', 'journey_restore']); ready = true; break; } catch { await new Promise(resolve => setTimeout(resolve, 500)); }
    }
    if (!ready) throw new Error('Isolated restore database did not become ready');
    docker(['exec', '-i', container, 'pg_restore', '--single-transaction', '--exit-on-error', '--no-owner', '--no-acl', '-U', 'journey', '-d', 'journey_restore'], plain);
    const before = snapshots(container, 'journey_restore', 'journey');
    const oldRuns = Number(pg(container, 'journey_restore', 'journey', 'SELECT count(*) FROM agent_runs;'));
    pg(container, 'journey_restore', 'journey', scrubSQL());
    const after = snapshots(container, 'journey_restore', 'journey');
    if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error('Restore scrub changed protected records');
    const remaining = JSON.parse(pg(container, 'journey_restore', 'journey', `SELECT json_build_object('runs',(SELECT count(*) FROM agent_runs),'tools',(SELECT count(*) FROM agent_tool_runs),'candidates',(SELECT count(*) FROM agent_confirmations),'threads',(SELECT count(*) FROM agent_threads),'agent_replays',(SELECT count(*) FROM idempotency_keys WHERE path LIKE '/api/v1/agent/%'),'active_sessions',(SELECT count(*) FROM auth_sessions WHERE revoked_at IS NULL));`));
    if (Object.values(remaining).some(value => value !== 0)) throw new Error('Restored privacy state is not empty');
    // Legacy 0007 archives do not contain the consent table; all others must be empty.
    const consentTable = pg(container, 'journey_restore', 'journey', "SELECT COALESCE(to_regclass('public.agent_consents')::text,'');");
    if (consentTable && Number(pg(container, 'journey_restore', 'journey', 'SELECT count(*) FROM agent_consents;')) !== 0) throw new Error('Restored consent remains');
    result = { success: true, source_archive: path.resolve(archive), source_dump_sha256: metadata.dump_sha256, scrub_sha256: createHash('sha256').update(scrubSQL()).digest('hex'), checked_at: new Date().toISOString(), source_agent_runs: oldRuns, remaining, protected_records: after, network: 'none', promoted: false, temporary_database_removed: true };
  } finally {
    if (created) {
      const [item] = JSON.parse(docker(['inspect', container]));
      if (item.Config.Labels?.['journey.privacy.restore'] === 'isolated') docker(['rm', '--force', container]);
    }
  }
  if (report) { privateDirectory(path.dirname(report)); fs.writeFileSync(report, JSON.stringify(result, null, 2), { mode: 0o600, flag: 'wx' }); }
  return result;
}

async function main() {
  const [command, ...args] = process.argv.slice(2);
  const values = {};
  for (let index = 0; index < args.length; index += 1) {
    const key = args[index];
    if (!key.startsWith('--')) throw new Error('Use explicit named options');
    values[key.slice(2)] = args[index + 1]?.startsWith('--') || index + 1 === args.length ? true : args[++index];
  }
  let result;
  if (command === 'init-key') {
    const filename = path.resolve(values['key-file']);
    privateDirectory(path.dirname(filename));
    fs.writeFileSync(filename, randomBytes(32), { mode: 0o600, flag: 'wx' });
    result = { key_file: filename, created: true, reminder: 'Keep this key private and separate; losing it makes archives unrecoverable.' };
  } else if (command === 'backup') {
    result = backup({ container: values.container, project: values.project, database: values.database, user: values.user, directory: values.directory, keyFile: values['key-file'], includeAgentState: values['include-agent-state'] === true, retentionDays: Number(values['retention-days'] ?? 7) });
  } else if (command === 'drill') {
    result = await drill({ archive: values.archive, keyFile: values['key-file'], report: values.report });
  } else if (command === 'prune') {
    result = pruneExpired(values.directory, values['key-file'], { apply: values.apply === true, confirm: values.confirm });
  } else {
    throw new Error('Commands: init-key, backup, drill, prune. Live restore is intentionally unsupported.');
  }
  console.log(JSON.stringify(result, null, 2));
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(() => { console.error('Journey backup operation refused or failed; no live restore was performed. Check the command, private file permissions and isolated-container state.'); process.exitCode = 1; });
}
