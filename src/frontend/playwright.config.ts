import { defineConfig, devices } from "@playwright/test";

// The E2E suite starts its own API (fresh SQLite file, offline LLM mode so it is free and deterministic)
// and its own Vite server on non-default ports, so it never touches the demo database.
const ROOT = "../..";
const API_PORT = 8765;
const WEB_PORT = 5199;

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    viewport: { width: 1400, height: 900 },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1400, height: 900 } } }],
  webServer: [
    {
      command: `rm -f /tmp/raw-e2e.db* /tmp/raw-e2e-ckpt.db* && cd ${ROOT} && .venv/bin/uvicorn raw.main:app --port ${API_PORT} --app-dir src/backend`,
      url: `http://127.0.0.1:${API_PORT}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        DATABASE_URL: "sqlite:////tmp/raw-e2e.db",
        CHECKPOINT_URL: "/tmp/raw-e2e-ckpt.db",
        LLM_MODE: "offline",
        GEMINI_API_KEY: "",
        GROQ_API_KEY: "",
        OTEL_EXPORTER_OTLP_ENDPOINT: "",
      },
    },
    {
      command: `npx vite --port ${WEB_PORT} --strictPort`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: false,
      env: { API_URL: `http://127.0.0.1:${API_PORT}` },
    },
  ],
});
