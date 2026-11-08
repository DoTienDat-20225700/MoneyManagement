import { defineConfig, devices } from '@playwright/test';
import {
  E2E_BASE_URL,
  E2E_API_URL,
  E2E_FRONTEND_PORT,
  E2E_BACKEND_PORT,
} from './e2e/constants';

const pythonBin = process.env.PYTHON_BIN || 'python3';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: E2E_BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: true,
  },
  projects: [
    {
      name: 'risk',
      testMatch: /.*\.risk\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    {
      name: 'safe',
      testMatch: /.*\.safe\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    {
      name: 'general',
      testMatch: /.*\.spec\.ts$/,
      testIgnore: [/auth\.setup\.ts/, /\.(risk|safe)\.spec\.ts$/],
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
  webServer: [
    {
      command: `cd ../backend && ${pythonBin} manage.py migrate --settings=hubSettings.settings_e2e && ${pythonBin} hubSettings/seed_e2e.py && ${pythonBin} manage.py runserver ${E2E_BACKEND_PORT} --noreload --settings=hubSettings.settings_e2e`,
      url: `http://127.0.0.1:${E2E_BACKEND_PORT}/api/`,
      reuseExistingServer: false,
      timeout: 120 * 1000,
    },
    {
      command: `VITE_API_URL=${E2E_API_URL} npm run dev -- --port ${E2E_FRONTEND_PORT} --strictPort`,
      url: E2E_BASE_URL,
      reuseExistingServer: false,
      timeout: 120 * 1000,
    },
  ],
});
