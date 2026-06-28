// Visual pass for the new web surfaces: Today, Calendar (rotation view), Nutrition, and the
// active-session logging UI (started via start-from-slot). node scripts/newsurfaces-shots.mjs
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
    headers: {
      "content-type": "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!res.ok)
    throw new Error(`${method} ${path} -> ${res.status}: ${(await res.text()).slice(0, 160)}`);
  return res.status === 204 ? null : res.json();
}
const tryApi = (m, p, t, b, l) =>
  api(m, p, t, b).catch((e) => {
    console.warn(`  ! ${l || p}: ${String(e.message).slice(0, 120)}`);
    return null;
  });

async function seed() {
  const sub = `surf-${randomUUID()}`;
  const t = await api("POST", "/v1/auth/dev", null, { sub, email: `${sub}@example.com` });
  const token = t.access_token;
  const list = (await tryApi("GET", "/v1/exercises?limit=50", token)) || { items: [] };
  const ex = (i) => list.items[i % list.items.length]?.id;
  const prog = await api("POST", "/v1/programs", token, {
    name: "Hypertrophy Block",
    goal: "hypertrophy",
  });
  let n = 0;
  for (const [name, rest] of [
    ["Push", false],
    ["Pull", false],
    ["Legs", false],
    ["Rest", true],
    ["Upper", false],
    ["Lower", false],
    ["Rest", true],
  ]) {
    const s = await api("POST", `/v1/programs/${prog.id}/slots`, token, {
      name,
      is_rest_day: rest,
    });
    if (!rest && list.items.length)
      for (let k = 0; k < 4; k++)
        await tryApi(
          "POST",
          `/v1/program-slots/${s.id}/exercises`,
          token,
          {
            exercise_id: ex(n++),
            target_sets: 4,
            target_reps_low: 8,
            target_reps_high: 12,
            rest_seconds: 120,
            rep_mode: "range",
          },
          "ex",
        );
  }
  await tryApi(
    "PATCH",
    `/v1/programs/${prog.id}`,
    token,
    {
      periodization_mode: "block",
      mesocycle_length_microcycles: 4,
      auto_deload: true,
      intensity_mode: "rpe",
    },
    "patch",
  );
  await tryApi("POST", `/v1/programs/${prog.id}/activate`, token, null, "activate");
  for (let d = 20; d >= 0; d -= 5)
    await api("POST", "/v1/body-metrics", token, { weight_kg: 82 - (20 - d) * 0.1 }).catch(
      () => null,
    );
  // Start a session pre-filled from the current slot -> logging UI.
  const sess = await tryApi(
    "POST",
    `/v1/programs/${prog.id}/start-session`,
    token,
    null,
    "start-session",
  );
  const sessionId = sess?.id || sess?.session?.id || null;
  console.log(`• seeded; session ${sessionId || "(none)"}`);
  return { token, refresh: t.refresh_token, sessionId };
}

async function run() {
  console.log("Seeding…");
  const s = await seed();
  const SHOTS = [
    { name: "today", path: "/", widths: [1440, 390], themes: ["light", "dark"] },
    { name: "calendar", path: "/calendar", widths: [1440], themes: ["light"] },
    { name: "nutrition", path: "/nutrition", widths: [1440], themes: ["light"] },
    ...(s.sessionId
      ? [{ name: "logging", path: `/workouts/${s.sessionId}`, widths: [1440], themes: ["light"] }]
      : []),
  ];
  const browser = await chromium.launch();
  const cookies = [
    { name: "gym_access", value: s.token, url: WEB, httpOnly: true, sameSite: "Lax" },
    { name: "gym_refresh", value: s.refresh, url: WEB, httpOnly: true, sameSite: "Lax" },
  ];
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
          await page.screenshot({
            path: `${OUT}new_${shot.name}_${w}_${theme}.png`,
            fullPage: true,
          });
          console.log(`  ✓ ${shot.name} ${w} ${theme}`);
        } catch (e) {
          console.warn(`  ✗ ${shot.name} ${w} ${theme}: ${String(e.message).slice(0, 120)}`);
        }
      }
    }
    await ctx.close();
  }
  await browser.close();
  console.log("Done.");
}
run().catch((e) => {
  console.error("FATAL:", e);
  process.exit(1);
});
