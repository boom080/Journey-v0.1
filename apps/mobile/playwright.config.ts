import { defineConfig, devices } from '@playwright/test';

const recordingDemo = process.env.DEMO_RECORDING === '1';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  outputDir: 'reports/e2e-results',
  reporter: [
    ['line'],
    ['junit', { outputFile: 'reports/e2e-junit.xml' }],
    ['html', { outputFolder: 'reports/playwright-html', open: 'never' }],
  ],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: recordingDemo ? 'on' : 'retain-on-failure',
    launchOptions: recordingDemo ? { slowMo: 700 } : undefined,
    ...devices['Desktop Chrome'],
  },
  webServer: {
    command: 'node e2e/static-server.mjs',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
