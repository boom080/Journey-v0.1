import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const configPath = require.resolve('../apps/mobile/app.config.js');

function loadVariant(variant) {
  process.env.APP_VARIANT = variant;
  delete require.cache[configPath];
  return require(configPath);
}

const expected = {
  development: ['Journey (Dev)', 'com.boom080.journey.dev', true],
  preview: ['Journey (Preview)', 'com.boom080.journey.preview', false],
  production: ['Journey', 'com.boom080.journey', false],
};

for (const [variant, [name, identifier, cleartext]] of Object.entries(expected)) {
  const config = loadVariant(variant);
  assert.equal(config.name, name);
  assert.equal(config.ios.bundleIdentifier, identifier);
  assert.equal(config.android.package, identifier);
  assert.equal(config.extra.appVariant, variant);
  const buildProperties = config.plugins.find(
    (plugin) => Array.isArray(plugin) && plugin[0] === 'expo-build-properties',
  );
  assert.ok(buildProperties, `${variant}: expo-build-properties missing`);
  assert.equal(buildProperties[1].android.usesCleartextTraffic, cleartext);
}

delete process.env.APP_VARIANT;
const eas = JSON.parse(fs.readFileSync(new URL('../apps/mobile/eas.json', import.meta.url), 'utf8'));
assert.equal(eas.build.development.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED, 'true');
assert.equal(eas.build.preview.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED, 'false');
assert.equal(eas.build.production.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED, 'false');

const envExample = fs.readFileSync(new URL('../.env.example', import.meta.url), 'utf8');
const testPassword = envExample
  .split(/\r?\n/)
  .find((line) => line.startsWith('TEST_ACCOUNT_PASSWORD='))
  ?.slice('TEST_ACCOUNT_PASSWORD='.length);
assert.ok(testPassword, '.env.example: TEST_ACCOUNT_PASSWORD missing');
assert.ok(
  Buffer.byteLength(testPassword, 'utf8') >= 10 &&
    Buffer.byteLength(testPassword, 'utf8') <= 72 &&
    /[a-z]/.test(testPassword) &&
    /[A-Z]/.test(testPassword) &&
    /\d/.test(testPassword),
  '.env.example: TEST_ACCOUNT_PASSWORD does not satisfy the backend password policy',
);

console.log(
  'Journey app variants and local test-account example verified: development, preview, production',
);
