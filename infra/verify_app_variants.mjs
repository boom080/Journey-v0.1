import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const configPath = require.resolve('../apps/mobile/app.config.js');

function loadVariant(variant, apiBaseUrl = undefined, enableDevelopmentCapabilities = true) {
  process.env.APP_VARIANT = variant;
  if (enableDevelopmentCapabilities) {
    process.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED = 'true';
    process.env.EXPO_PUBLIC_AGENT_DEBUG_DETAILS_ENABLED = 'true';
    process.env.SEED_TEST_ACCOUNT = 'true';
    process.env.TEST_ACCOUNT_EMAIL = 'demo@journey.local';
    process.env.TEST_ACCOUNT_PASSWORD = 'JourneyDemo2026';
  } else {
    delete process.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED;
    delete process.env.EXPO_PUBLIC_AGENT_DEBUG_DETAILS_ENABLED;
    delete process.env.SEED_TEST_ACCOUNT;
    delete process.env.TEST_ACCOUNT_EMAIL;
    delete process.env.TEST_ACCOUNT_PASSWORD;
  }
  if (apiBaseUrl === undefined) {
    delete process.env.EXPO_PUBLIC_API_BASE_URL;
  } else {
    process.env.EXPO_PUBLIC_API_BASE_URL = apiBaseUrl;
  }
  delete require.cache[configPath];
  return require(configPath);
}

const expected = {
  development: ['Journey (Dev)', 'com.boom080.journey.dev', true],
  preview: ['Journey (Preview)', 'com.boom080.journey.preview', false],
  production: ['Journey', 'com.boom080.journey', false],
};

for (const [variant, [name, identifier, cleartext]] of Object.entries(expected)) {
  const config = loadVariant(
    variant,
    variant === 'development' ? undefined : 'https://journey.example.com',
  );
  assert.equal(config.name, name);
  assert.equal(config.ios.bundleIdentifier, identifier);
  assert.equal(config.android.package, identifier);
  assert.equal(config.extra.appVariant, variant);
  assert.deepEqual(config.extra.capabilities, {
    foodImageAnalysis: variant === 'development',
    localTestAccount: variant === 'development',
    agentDebugDetails: variant === 'development',
  });
  assert.deepEqual(
    config.extra.localTestAccount,
    variant === 'development'
      ? { identifier: 'demo@journey.local', password: 'JourneyDemo2026' }
      : null,
  );
  const buildProperties = config.plugins.find(
    (plugin) => Array.isArray(plugin) && plugin[0] === 'expo-build-properties',
  );
  assert.ok(buildProperties, `${variant}: expo-build-properties missing`);
  assert.equal(buildProperties[1].android.usesCleartextTraffic, cleartext);
}

const failClosedDevelopment = loadVariant('development', undefined, false);
assert.deepEqual(failClosedDevelopment.extra.capabilities, {
  foodImageAnalysis: false,
  localTestAccount: false,
  agentDebugDetails: false,
});
assert.equal(failClosedDevelopment.extra.localTestAccount, null);

assert.throws(
  () => loadVariant('production', 'http://journey.example.com'),
  /require an HTTPS EXPO_PUBLIC_API_BASE_URL/,
);

delete process.env.APP_VARIANT;
delete process.env.EXPO_PUBLIC_API_BASE_URL;
delete process.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED;
delete process.env.EXPO_PUBLIC_AGENT_DEBUG_DETAILS_ENABLED;
delete process.env.SEED_TEST_ACCOUNT;
delete process.env.TEST_ACCOUNT_EMAIL;
delete process.env.TEST_ACCOUNT_PASSWORD;
const eas = JSON.parse(fs.readFileSync(new URL('../apps/mobile/eas.json', import.meta.url), 'utf8'));
assert.equal(eas.build.development.environment, 'development');
assert.equal(eas.build.preview.environment, 'preview');
assert.equal(eas.build.production.environment, 'production');
assert.equal(eas.build.development.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED, 'true');
assert.equal(eas.build.preview.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED, 'false');
assert.equal(eas.build.production.env.EXPO_PUBLIC_FOOD_IMAGE_ANALYSIS_ENABLED, 'false');
assert.equal(eas.build.development.env.EXPO_PUBLIC_AGENT_DEBUG_DETAILS_ENABLED, 'true');
assert.equal(eas.build.preview.env.EXPO_PUBLIC_AGENT_DEBUG_DETAILS_ENABLED, 'false');
assert.equal(eas.build.production.env.EXPO_PUBLIC_AGENT_DEBUG_DETAILS_ENABLED, 'false');

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
