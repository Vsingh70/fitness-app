import { expect, test, type BrowserContext, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Runtime performance suite (the "does it feel slow" layer).
 *
 * Measures, against a running app, the things the audit flagged: Largest
 * Contentful Paint and Cumulative Layout Shift per route, the time a client-side
 * route transition takes, and any long tasks that block the main thread during a
 * transition. Budgets live in perf/budgets.json and are ratchets.
 *
 * Requires the API and web dev server running (same as the existing e2e):
 *   API: cd apps/api && uv run uvicorn app.main:app --port 8000
 *   Web: cd apps/web && pnpm dev
 * Run: pnpm perf:e2e
 */

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const budgets = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../perf/budgets.json"), "utf8"),
);
const V = budgets.webVitals;
const ROUTES: string[] = budgets.routesToProbe;
const API = "http://127.0.0.1:8000";

interface PerfWindow {
  __perf: { lcp: number; cls: number; longTasks: number[] };
}

/**
 * Mark the onboarding tour as already seen before any app code runs, so the
 * spotlight-tour overlay never auto-starts for the fresh perf user and steal the
 * clicks. This measures route transitions for a returning user (the realistic
 * steady state), not the first-run tutorial. It does not relax any budget.
 */
const SEED_RETURNING_USER = () => {
  try {
    window.localStorage.setItem("om.tutorial.seen", "true");
    window.localStorage.setItem(
      "om.tutorial.pages",
      JSON.stringify(["/workouts", "/programs", "/nutrition", "/analytics", "/settings"]),
    );
  } catch {
    // localStorage may be unavailable in some contexts; degrade gracefully.
  }
};

/** Install web-vitals observers before any app code runs. */
const OBSERVER = () => {
  const w = window as unknown as PerfWindow;
  w.__perf = { lcp: 0, cls: 0, longTasks: [] };
  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) w.__perf.lcp = (e as PerformanceEntry).startTime;
    }).observe({ type: "largest-contentful-paint", buffered: true });
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        const ls = e as PerformanceEntry & { value: number; hadRecentInput: boolean };
        if (!ls.hadRecentInput) w.__perf.cls += ls.value;
      }
    }).observe({ type: "layout-shift", buffered: true });
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) w.__perf.longTasks.push(e.duration);
    }).observe({ type: "longtask", buffered: true });
  } catch {
    // Some entry types may be unsupported in a given browser; degrade gracefully.
  }
};

async function signIn(context: BrowserContext): Promise<void> {
  const sub = `perf-${randomUUID()}`;
  const res = await fetch(`${API}/v1/auth/dev`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sub, email: `${sub}@example.com` }),
  });
  if (!res.ok) throw new Error(`dev sign-in failed: ${res.status}`);
  const tokens = (await res.json()) as { access_token: string; refresh_token: string };
  const expires = Math.floor(Date.now() / 1000) + 60 * 24 * 60 * 60;
  await context.addCookies([
    { name: "gym_access", value: tokens.access_token, domain: "127.0.0.1", path: "/", httpOnly: true, sameSite: "Lax", expires },
    { name: "gym_refresh", value: tokens.refresh_token, domain: "127.0.0.1", path: "/", httpOnly: true, sameSite: "Lax", expires },
  ]);
}

async function readVitals(page: Page) {
  // Give LCP a moment to settle after the network is idle.
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(400);
  return page.evaluate(() => (window as unknown as PerfWindow).__perf);
}

test.beforeEach(async ({ context }) => {
  await context.addInitScript(SEED_RETURNING_USER);
  await context.addInitScript(OBSERVER);
  await signIn(context);
});

for (const route of ROUTES) {
  test(`web vitals within budget: ${route}`, async ({ page }) => {
    await page.goto(route);
    const perf = await readVitals(page);

    expect(perf.lcp, `LCP on ${route} was ${perf.lcp.toFixed(0)}ms`).toBeLessThanOrEqual(V.lcpMs);
    expect(perf.cls, `CLS on ${route} was ${perf.cls.toFixed(3)}`).toBeLessThanOrEqual(V.clsMax);
  });
}

test("route transitions are fast and do not block the main thread", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  // Probe a few client-side transitions via the nav. Uses hrefs from NAV_ITEMS.
  const targets = ["/workouts", "/programs", "/nutrition", "/analytics"];
  for (const href of targets) {
    const before = await page.evaluate(
      () => (window as unknown as PerfWindow).__perf.longTasks.length,
    );
    const start = Date.now();
    await page.locator(`a[href="${href}"]`).first().click();
    await page.waitForURL(`**${href}`);
    // Destination "content painted" signal. Routes lead with their primary
    // heading at h1 or (programs onboarding) h2, or an explicit data-page-title.
    await page.locator("h1, h2, [data-page-title]").first().waitFor({ state: "visible" });
    const elapsed = Date.now() - start;

    const longTasks = await page.evaluate(
      () => (window as unknown as PerfWindow).__perf.longTasks,
    );
    const newLongTasks = longTasks.slice(before);
    const worst = newLongTasks.length ? Math.max(...newLongTasks) : 0;

    expect(elapsed, `transition to ${href} took ${elapsed}ms`).toBeLessThanOrEqual(
      V.routeTransitionMs,
    );
    expect(
      worst,
      `worst long task during transition to ${href} was ${worst.toFixed(0)}ms`,
    ).toBeLessThanOrEqual(V.longTaskDuringTransitionMsMax);
  }
});
