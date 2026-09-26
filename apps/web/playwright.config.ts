import { defineConfig, devices } from "@playwright/test";

const WEB_PORT = 3101;
const API_PORT = 8011;

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    reducedMotion: "reduce",
    colorScheme: "dark",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Fresh database every run so tests never see agents or runs left by an earlier suite.
      command: `rm -f /tmp/eap-e2e.db /tmp/eap-e2e-checkpoints.db && cd ../api && ./.venv/bin/python -m uvicorn app.main:app --port ${API_PORT}`,
      url: `http://localhost:${API_PORT}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        PLAYGROUND_FAKE_LLM: "true",
        PLAYGROUND_DATABASE_URL: "sqlite:////tmp/eap-e2e.db",
        PLAYGROUND_INTERNAL_KEY: "e2e-internal-key",
        PLAYGROUND_SELF_URL: "http://127.0.0.1:8011",  // the sandbox subprocesses call the API over HTTP
        PLAYGROUND_ENVIRONMENT: "e2e",
        PLAYGROUND_RATE_LIMIT_PER_MINUTE: "0",
      },
    },
    {
      // A second `next dev` in the same directory is refused, so tests run a production build on its own port.
      command: `npm run build && npm run start -- --port ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}/api/health`,
      reuseExistingServer: false,
      timeout: 300_000,
      env: {
        PLAYGROUND_API_URL: `http://localhost:${API_PORT}`,
        PLAYGROUND_INTERNAL_KEY: "e2e-internal-key",
        ALLOW_DEV_LOGIN: "true",
        AUTH_SECRET: "e2e-only-session-secret-not-for-production",
      },
    },
  ],
});
