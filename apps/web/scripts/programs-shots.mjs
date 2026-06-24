// Visual-verification harness for the Programs redesign.
// Dev-signs-in, seeds a program (slots incl. rest days + exercises, activated) and a
// saved template via the new API, then screenshots every Programs surface at
// 390 / 834 / 1440 px in light + dark. Run from apps/web: `node scripts/programs-shots.mjs`
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
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${method} ${path} -> ${res.status}: ${text.slice(0, 300)}`);
  }
  return res.status === 204 ? null : res.json();
}

async function tryApi(method, path, token, body, label) {
  try {
    return await api(method, path, token, body);
  } catch (e) {
    console.warn(`  ! ${label || path} skipped: ${String(e.message).slice(0, 160)}`);
    return null;
  }
}

async function seed() {
  const sub = `shots-${randomUUID()}`;
  const tokens = await api("POST", "/v1/auth/dev", null, { sub, email: `${sub}@example.com` });
  const token = tokens.access_token;
  console.log("• signed in dev user");

  // Reuse existing exercises if the dev DB has any; otherwise create a spread.
  let list = (await tryApi("GET", "/v1/exercises?limit=50", token, null, "list exercises")) || { items: [] };
  let exercises = list.items || [];
  if (exercises.length < 4) {
    const defs = [
      ["Bench Press", "chest", "barbell", "horizontal_push"],
      ["Incline Dumbbell Press", "chest", "dumbbell", "horizontal_push"],
      ["Barbell Row", "back", "barbell", "horizontal_pull"],
      ["Lat Pulldown", "back", "cable", "vertical_pull"],
      ["Back Squat", "quads", "barbell", "squat"],
      ["Romanian Deadlift", "hamstrings", "barbell", "hinge"],
      ["Overhead Press", "shoulders", "barbell", "vertical_push"],
      ["Leg Press", "quads", "machine", "squat"],
    ];
    for (const [name, primary_muscle, equipment, movement_pattern] of defs) {
      const ex = await tryApi("POST", "/v1/exercises", token, {
        name, primary_muscle, secondary_muscles: [], equipment, movement_pattern,
        tracking_type: "weight_reps", is_unilateral: false,
      }, `create ${name}`);
      if (ex) exercises.push(ex);
    }
  }
  console.log(`• ${exercises.length} exercises available`);
  const ex = (i) => exercises[i % exercises.length].id;

  // Primary program: a 7-slot microcycle (5 training + 2 rest), periodized, activated.
  const prog = await api("POST", "/v1/programs", token, {
    name: "Hypertrophy Block", description: "Upper/lower emphasis", goal: "hypertrophy",
  });
  const pid = prog.id;
  const slots = [
    ["Push", false], ["Pull", false], ["Legs", false], ["Rest", true],
    ["Upper", false], ["Lower", false], ["Rest", true],
  ];
  let createdSlots = [];
  for (const [name, is_rest_day] of slots) {
    const s = await api("POST", `/v1/programs/${pid}/slots`, token, { name, is_rest_day });
    createdSlots.push(s);
    if (!is_rest_day && exercises.length) {
      for (let k = 0; k < 4; k++) {
        await tryApi("POST", `/v1/program-slots/${s.id}/exercises`, token, {
          exercise_id: ex(createdSlots.length + k), target_sets: 4,
          target_reps_low: 8, target_reps_high: 12, rest_seconds: 120,
          rep_mode: "range", progression_strategy: "double_progression",
        }, `add exercise to ${name}`);
      }
    }
  }
  await tryApi("PATCH", `/v1/programs/${pid}`, token, {
    periodization_mode: "block", mesocycle_length_microcycles: 4, auto_deload: true, intensity_mode: "rpe",
  }, "patch periodization");
  await tryApi("POST", `/v1/programs/${pid}/activate`, token, null, "activate");
  // Advance the rotation a few times so the cycle bar + today card show progress.
  for (let i = 0; i < 8; i++) await tryApi("POST", `/v1/programs/${pid}/advance`, token, null, "advance");
  const trainingSlot = createdSlots.find((s) => !s.is_rest_day);
  console.log(`• seeded + activated program ${pid}`);

  // A second program saved as a shared template (populates the library + browse).
  const prog2 = await api("POST", "/v1/programs", token, { name: "Strength 5x5", goal: "strength" });
  for (const [name, is_rest_day] of [["Day A", false], ["Day B", false], ["Rest", true]]) {
    const s = await api("POST", `/v1/programs/${prog2.id}/slots`, token, { name, is_rest_day });
    if (!is_rest_day && exercises.length)
      for (let k = 0; k < 3; k++)
        await tryApi("POST", `/v1/program-slots/${s.id}/exercises`, token,
          { exercise_id: ex(k), target_sets: 5, target_reps_low: 5, target_reps_high: 5, rest_seconds: 180, rep_mode: "target" }, "add 5x5 ex");
  }
  let templateSlug = null;
  const saved = await tryApi("POST", `/v1/programs/${prog2.id}/save-as-template`, token,
    { name: "5x5 Strength (Shared)", visibility: "shared" }, "save-as-template");
  if (saved?.template?.slug) templateSlug = saved.template.slug;
  console.log(`• second program + template (${templateSlug || "no slug"})`);

  return { token, expires_in: tokens.expires_in, refresh: tokens.refresh_token, pid, trainingSlotId: trainingSlot?.id, templateSlug };
}

const SHOTS = (s) => [
  { name: "spine", path: "/programs", widths: [1440, 834, 390], themes: ["light", "dark"] },
  { name: "builder", path: `/programs/${s.pid}/edit`, widths: [1440, 390], themes: ["light", "dark"] },
  { name: "browse", path: "/programs/templates", widths: [1440, 834], themes: ["light"] },
  { name: "chooser", path: "/programs/new", widths: [1440, 390], themes: ["light"] },
  ...(s.trainingSlotId ? [{ name: "slot-detail", path: `/programs/${s.pid}/days/${s.trainingSlotId}`, widths: [1440], themes: ["light"] }] : []),
  ...(s.templateSlug ? [{ name: "template-detail", path: `/programs/templates/${s.templateSlug}`, widths: [1440], themes: ["light"] }] : []),
];

async function run() {
  console.log("Seeding…");
  const s = await seed();
  const browser = await chromium.launch();
  const cookies = [
    { name: "gym_access", value: s.token, url: WEB, httpOnly: true, sameSite: "Lax" },
    { name: "gym_refresh", value: s.refresh, url: WEB, httpOnly: true, sameSite: "Lax" },
  ];
  const made = [];
  for (const theme of ["light", "dark"]) {
    const ctx = await browser.newContext({ colorScheme: theme, deviceScaleFactor: 2 });
    await ctx.addCookies(cookies);
    const page = await ctx.newPage();
    for (const shot of SHOTS(s)) {
      if (!shot.themes.includes(theme)) continue;
      for (const w of shot.widths) {
        await page.setViewportSize({ width: w, height: 900 });
        try {
          await page.goto(`${WEB}${shot.path}`, { waitUntil: "networkidle", timeout: 30000 });
          await page.waitForTimeout(1100); // let entrance motion settle
          const file = `${OUT}${shot.name}_${w}_${theme}.png`;
          await page.screenshot({ path: file, fullPage: true });
          made.push(file);
          console.log(`  ✓ ${shot.name} ${w} ${theme}`);
        } catch (e) {
          console.warn(`  ✗ ${shot.name} ${w} ${theme}: ${String(e.message).slice(0, 140)}`);
        }
      }
    }
    await ctx.close();
  }
  await browser.close();
  console.log(`\nDone. ${made.length} screenshots in ${OUT}`);
}

run().catch((e) => { console.error("FATAL:", e); process.exit(1); });
