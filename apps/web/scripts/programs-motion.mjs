// Motion-verification harness: records a short walkthrough of the Programs motion —
// staggered spine reveal + cycle-bar fill, library-row hover (Deactivate), and the
// builder slot-rail drag-reorder. Run from apps/web: `node scripts/programs-motion.mjs`
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { randomUUID } from "node:crypto";

const API = "http://127.0.0.1:8000";
const WEB = "http://127.0.0.1:3000";
const DIR = new URL("../.recordings/", import.meta.url).pathname;
mkdirSync(DIR, { recursive: true });

async function api(method, path, token, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.status === 204 ? null : res.json();
}
const tryApi = (m, p, t, b) => api(m, p, t, b).catch(() => null);

async function seed() {
  const sub = `motion-${randomUUID()}`;
  const tok = (await api("POST", "/v1/auth/dev", null, { sub, email: `${sub}@example.com` })).access_token;
  const list = (await tryApi("GET", "/v1/exercises?limit=50", tok)) || { items: [] };
  const ex = (i) => list.items[i % list.items.length]?.id;
  const prog = await api("POST", "/v1/programs", tok, { name: "Hypertrophy Block", goal: "hypertrophy" });
  const slots = [["Push", false], ["Pull", false], ["Legs", false], ["Rest", true], ["Upper", false], ["Lower", false], ["Rest", true]];
  let n = 0;
  for (const [name, is_rest_day] of slots) {
    const s = await api("POST", `/v1/programs/${prog.id}/slots`, tok, { name, is_rest_day });
    if (!is_rest_day && list.items.length) for (let k = 0; k < 3; k++)
      await tryApi("POST", `/v1/program-slots/${s.id}/exercises`, tok, { exercise_id: ex(n++), target_sets: 4, target_reps_low: 8, target_reps_high: 12, rest_seconds: 120, rep_mode: "range" });
  }
  await tryApi("PATCH", `/v1/programs/${prog.id}`, tok, { periodization_mode: "block", mesocycle_length_microcycles: 4, auto_deload: true, intensity_mode: "rpe" });
  await tryApi("POST", `/v1/programs/${prog.id}/activate`, tok, null);
  for (let i = 0; i < 6; i++) await tryApi("POST", `/v1/programs/${prog.id}/advance`, tok, null);
  return { tok, refresh: (await api("POST", "/v1/auth/dev", null, { sub: `${sub}-r`, email: "x@x.com" })).refresh_token, pid: prog.id };
}

async function dragSlot(page, fromName, toName) {
  const grip = page.locator(".ew-dtab", { hasText: fromName }).locator(".gr");
  const target = page.locator(".ew-dtab", { hasText: toName });
  const g = await grip.boundingBox();
  const t = await target.boundingBox();
  if (!g || !t) { console.warn("  ! drag: boxes not found"); return; }
  await page.mouse.move(g.x + g.width / 2, g.y + g.height / 2);
  await page.mouse.down();
  await page.waitForTimeout(150);
  const steps = 16;
  for (let i = 1; i <= steps; i++) {
    await page.mouse.move(g.x + g.width / 2, g.y + ((t.y - g.y) * i) / steps);
    await page.waitForTimeout(45);
  }
  await page.waitForTimeout(200);
  await page.mouse.up();
  await page.waitForTimeout(900);
}

async function run() {
  console.log("Seeding…");
  const s = await seed();
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    colorScheme: "light",
    recordVideo: { dir: DIR, size: { width: 1440, height: 900 } },
  });
  await ctx.addCookies([
    { name: "gym_access", value: s.tok, url: WEB, httpOnly: true, sameSite: "Lax" },
    { name: "gym_refresh", value: s.refresh, url: WEB, httpOnly: true, sameSite: "Lax" },
  ]);
  const page = await ctx.newPage();

  // 1. Spine: staggered reveal + cycle-bar fill on load.
  await page.goto(`${WEB}/programs`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2600);
  // 2. Library row hover -> Deactivate affordance.
  try {
    const row = page.locator(".aw-prog-row").first();
    await row.scrollIntoViewIfNeeded();
    await row.hover();
    await page.waitForTimeout(1400);
  } catch (e) { console.warn("  ! hover:", String(e.message).slice(0, 100)); }
  // 3. Builder: slot-rail drag-reorder (spring layout).
  await page.goto(`${WEB}/programs/${s.pid}/edit`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1600);
  try { await dragSlot(page, "Lower", "Push"); } catch (e) { console.warn("  ! drag:", String(e.message).slice(0, 120)); }
  await page.waitForTimeout(800);

  const video = page.video();
  await ctx.close();
  const dest = `${DIR}programs-motion.webm`;
  await video.saveAs(dest);
  await browser.close();
  console.log(`Done. Recording: ${dest}`);
}

run().catch((e) => { console.error("FATAL:", e); process.exit(1); });
