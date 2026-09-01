import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { seal, unseal, prunePlan, pruneExpired, scrubSQL } from './backup.mjs';

const plain = Buffer.from('synthetic-health-backup-no-real-users');
const key = randomBytes(32);
const metadata = { created_at: '2026-08-30T00:00:00Z', expires_at: '2026-09-06T00:00:00Z', dump_sha256: createHash('sha256').update(plain).digest('hex') };

test('AES-GCM round trip does not expose the dump', () => {
  const sealed = seal(plain, key, metadata);
  assert.equal(sealed.includes(plain), false);
  assert.deepEqual(unseal(sealed, key, { now: new Date('2026-08-31') }).plain, plain);
});

test('altered metadata, ciphertext and wrong key fail authentication', () => {
  const sealed = seal(plain, key, metadata);
  const modified = JSON.parse(sealed);
  modified.metadata.expires_at = '2099-01-01T00:00:00Z';
  assert.throws(() => unseal(Buffer.from(JSON.stringify(modified)), key));
  const data = JSON.parse(sealed);
  data.data = Buffer.from('tampered').toString('base64');
  assert.throws(() => unseal(Buffer.from(JSON.stringify(data)), key));
  assert.throws(() => unseal(sealed, randomBytes(32)));
});

test('expired and excessive-retention backups cannot be restored', () => {
  assert.throws(() => unseal(seal(plain, key, metadata), key, { now: new Date('2026-09-07') }), /expired/);
  assert.throws(() => unseal(seal(plain, key, { ...metadata, expires_at: '2099-01-01T00:00:00Z' }), key));
});

test('prune only plans authenticated managed files, leaving legacy files and symlinks alone', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'journey-backup-test-'));
  const keyFile = path.join(temp, 'key');
  const archive = path.join(temp, 'journey-00000000-0000-0000-0000-000000000000.jbackup');
  try {
    fs.writeFileSync(keyFile, key, { mode: 0o600 });
    fs.writeFileSync(archive, seal(plain, key, metadata), { mode: 0o600 });
    fs.writeFileSync(path.join(temp, 'legacy.dump'), plain);
    fs.symlinkSync(archive, path.join(temp, 'journey-00000000-0000-0000-0000-000000000001.jbackup'));
    const plan = prunePlan(temp, keyFile, new Date('2026-09-07'));
    assert.deepEqual(plan.map(item => item.path), [archive]);
    assert.ok(fs.existsSync(archive)); // dry-run: nothing deleted
  } finally {
    fs.rmSync(temp, { recursive: true }); // this test's mkdtemp only
  }
});

test('restore scrub invalidates Agent state and sessions without deleting health records', () => {
  const sql = scrubSQL().toString();
  for (const table of ['agent_runs', 'agent_threads', 'agent_consents', 'agent_confirmations']) assert.match(sql, new RegExp(`DELETE FROM public.${table}`));
  assert.match(sql, /revoked_at = now\(\)/);
  for (const table of ['food_records', 'activity_records', 'weight_records', 'users']) assert.doesNotMatch(sql, new RegExp(`DELETE FROM public.${table}`));
});

test('confirmed prune deletes only expired managed archives, never key or unrelated files', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'journey-prune-test-'));
  const keyFile = path.join(temp, 'key');
  const archive = path.join(temp, 'journey-00000000-0000-0000-0000-000000000000.jbackup');
  try {
    fs.writeFileSync(keyFile, key, { mode: 0o600 });
    fs.writeFileSync(archive, seal(plain, key, metadata), { mode: 0o600 });
    fs.writeFileSync(path.join(temp, 'legacy.dump'), plain);
    const now = new Date('2026-09-07');
    assert.throws(() => pruneExpired(temp, keyFile, { apply: true, now }), /confirmation required/);
    assert.ok(fs.existsSync(archive));
    const result = pruneExpired(temp, keyFile, { apply: true, confirm: 'delete-expired-journey-backups', now });
    assert.equal(result.removed, 1);
    assert.equal(fs.existsSync(archive), false);
    assert.ok(fs.existsSync(keyFile));
    assert.ok(fs.existsSync(path.join(temp, 'legacy.dump')));
  } finally {
    fs.rmSync(temp, { recursive: true }); // this test's mkdtemp only
  }
});
