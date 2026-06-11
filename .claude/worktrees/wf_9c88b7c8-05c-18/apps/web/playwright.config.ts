import { defineConfig, devices } from "@playwright/test";

/**
 * Assumes the API and the web dev server are both running:
 *   - API: cd apps/api && uv run uvicorn app.main:app --port 8000
 *   - Web: cd apps/web && pnpm dev
 * Spec is small; no auto-start to keep the e2e launchable in CI later
 * via a separate compose-up step.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
