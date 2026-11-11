import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: 'auth-contract.spec.ts',
  workers: 1,
  timeout: 10000,
  reporter: 'list',
  use: { ...devices['Desktop Chrome'], baseURL: 'http://127.0.0.1:5178', trace: 'retain-on-failure' },
  webServer: {
    command: 'VITE_API_URL=/api npm run dev -- --host 127.0.0.1 --port 5178 --strictPort',
    url: 'http://127.0.0.1:5178',
    reuseExistingServer: false,
  },
});
