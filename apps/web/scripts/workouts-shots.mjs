// Visual verification for the Workouts hub + IA consolidation.
// Seeds an active program (Train card) + body weight (Health Metrics), then screenshots
// the 6-item nav, the Workouts hub, and the merged Health at 390/834/1440 light+dark.
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { randomUUID } from "node:crypto";

const API = "http://127.0.0.1:8000";
const WEB = "http://127.0.0.1:3000";
const OUT = new URL("../.screenshots/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

async function api(method, path, token, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status}: ${(await res.text()).slice(0, 160)}`);
  return res.status === 204 ? null : res.json();
}
const tryApi = (m, p, t, b, lbl) => api(m, p, t, b).catch((e) => { console.warn(`  ! ${lbl || p}: ${String(e.message).slice(0, 120)}`); return null; });

async function seed() {
  const sub = `web-verify-${randomUUID()}`;
  const t = await api("POST", "/v1/auth/dev", null, { sub, email: `${sub}@example.com` });
  const token = t.access_token;
  const list = (await tryApi("GET", "/v1/exercises?limit=50", token)) || { items: [] };
  const ex = (i) => list.items[i % list.items.length]?.id;

  // Active program -> drives the Workouts hub "Train" card via rotation position.
  const prog = await api("POST", "/v1/programs", token, { name: "Hypertrophy Block", goal: "hypertrophy" });
  let n = 0;
  for (const [name, rest] of [["Push", false], ["Pull", false], ["Legs", false], ["Rest", true], ["Upper", false], ["Lower", false], ["Rest", true]]) {
    const s = await api("POST", `/v1/programs/${prog.id}/slots`, token, { name, is_rest_day: rest });
    if (!rest && list.items.length) for (let k = 0; k < 4; k++)
      await tryApi("POST", `/v1/program-slots/${s.id}/exercises`, token, { exercise_id: ex(n++), target_sets: 4, target_reps_low: 8, target_reps_high: 12, rest_seconds: 120, rep_mode: "range" }, "add ex");
  }
  await tryApi("PATCH", `/v1/programs/${prog.id}`, token, { periodization_mode: "block", mesocycle_length_microcycles: 4, auto_deload: true, intensity_mode: "rpe" }, "patch");
  await tryApi("POST", `/v1/programs/${prog.id}/activate`, token, null, "activate");
  for (let i = 0; i < 4; i++) await tryApi("POST", `/v1/programs/${prog.id}/advance`, token, null, "advance");

  // Body weight history -> Health "Metrics" section. Try a couple of payload shapes.
  for (let d = 30; d >= 0; d -= 5) {
    const day = `2026-0${d > 20 ? "5" : "6"}-${String(((d % 28) + 1)).padStart(2, "0")}`;
    const w = 82 - (30 - d) * 0.1;
    const ok = await api("POST", "/v1/body-metrics", token, { weight_kg: Number(w.toFixed(1)), recorded_at: day }).catch(() => null);
    if (!ok) await api("POST", "/v1/body-metrics", token, { weight_kg: Number(w.toFixed(1)) }).catch(() => null);
  }
  console.log(`• seeded program ${prog.id} + body metrics for ${sub}`);
  return { token, refresh: t.refresh_token };
}

const SHOTS = [
  { name: "workouts-hub", path: "/workouts", widths: [1440, 834, 390], themes: ["light", "dark"] },
  { name: "health-merged", path: "/health", widths: [1440, 390], themes: ["light", "dark"] },
  { name: "body-redirect", path: "/body", widths: [1440], themes: ["light"] }, // should land on /health
];

async function run() {
  console.log("Seeding…");
  const s = await seed();
  const browser = await chromium.launch();
  const cookies = [
    { name: "gym_access", value: s.token, url: WEB, httpOnly: true, sameSite: "Lax" },
    { name: "gym_refresh", value: s.refresh, url: WEB, httpOnly: true, sameSite: "Lax" },
  ];
  let made = 0;
  for (const theme of ["light", "dark"]) {
    const ctx = await browser.newContext({ colorScheme: theme, deviceScaleFactor: 2 });
    await ctx.addCookies(cookies);
    const page = await ctx.newPage();
    for (const shot of SHOTS) {
      if (!shot.themes.includes(theme)) continue;
      for (const w of shot.widths) {
        await page.setViewportSize({ width: w, height: 900 });
        try {
          await page.goto(`${WEB}${shot.path}`, { waitUntil: "networkidle", timeout: 30000 });
          await page.waitForTimeout(1200);
          await page.screenshot({ path: `${OUT}ia_${shot.name}_${w}_${theme}.png`, fullPage: true });
          made++; console.log(`  ✓ ${shot.name} ${w} ${theme} (url: ${page.url().replace(WEB, "")})`);
        } catch (e) { console.warn(`  ✗ ${shot.name} ${w} ${theme}: ${String(e.message).slice(0, 120)}`); }
      }
    }
    await ctx.close();
  }
  await browser.close();
  console.log(`\nDone. ${made} screenshots in ${OUT}`);
}
run().catch((e) => { console.error("FATAL:", e); process.exit(1); });
