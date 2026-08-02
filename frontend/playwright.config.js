import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: "http://127.0.0.1:8799",
    trace: "on-first-retry",
  },
  webServer: {
    command: "LOTUS_UI_HOST=127.0.0.1 LOTUS_UI_PORT=8799 LOTUS_UI_SESSION_SECRET=e2e-secret python3 server.py",
    url: "http://127.0.0.1:8799/",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
