// Comprehensive seed for the iOS dev user (ios-dev-user) so the wired iOS surfaces show
// live data: active program, body weights, and a finished session. node scripts/ios-verify-seed.mjs
const API = "http://127.0.0.1:8000";
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
const t = (m, p, tok, b, l) =>
  api(m, p, tok, b).catch((e) => {
    console.warn(`  ! ${l || p}: ${String(e.message).slice(0, 120)}`);
    return null;
  });

const tok = (
  await api("POST", "/v1/auth/dev", null, {
    sub: "ios-dev-user",
    email: "ios-dev-user@example.com",
  })
).access_token;
console.log("• ios-dev-user signed in");
const list = (await t("GET", "/v1/exercises?limit=50", tok)) || { items: [] };
const ex = (i) => list.items[i % list.items.length]?.id;

// clean prior programs
const existing = (await t("GET", "/v1/programs?limit=100", tok)) || { items: [] };
for (const p of existing.items || []) await t("DELETE", `/v1/programs/${p.id}`, tok);

const prog = await api("POST", "/v1/programs", tok, {
  name: "Hypertrophy Block",
  description: "Upper/lower",
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
  const s = await api("POST", `/v1/programs/${prog.id}/slots`, tok, { name, is_rest_day: rest });
  if (!rest && list.items.length)
    for (let k = 0; k < 4; k++)
      await t(
        "POST",
        `/v1/program-slots/${s.id}/exercises`,
        tok,
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
await t(
  "PATCH",
  `/v1/programs/${prog.id}`,
  tok,
  {
    periodization_mode: "block",
    mesocycle_length_microcycles: 4,
    auto_deload: true,
    intensity_mode: "rpe",
  },
  "patch",
);
await t("POST", `/v1/programs/${prog.id}/activate`, tok, null, "activate");

// body weights -> Health Metrics
for (let d = 20; d >= 0; d -= 5)
  await t("POST", "/v1/body-metrics", tok, { weight_kg: 82 - (20 - d) * 0.1 }, "weight");

// a finished session -> Workouts history + Insights volume
const sess = await t("POST", `/v1/programs/${prog.id}/start-session`, tok, null, "start");
if (sess?.id) {
  const we = (sess.exercises || sess.workout_exercises || [])[0];
  const weId = we?.id;
  if (weId) {
    await t("POST", `/v1/workout-exercises/${weId}/sets`, tok, { weight_kg: 60, reps: 10 }, "set1");
    await t("POST", `/v1/workout-exercises/${weId}/sets`, tok, { weight_kg: 60, reps: 9 }, "set2");
  }
  await t("POST", `/v1/workout-sessions/${sess.id}/finish`, tok, null, "finish");
  console.log(`• finished a session ${sess.id}`);
}
console.log(`• seeded ios-dev-user: program ${prog.id} active, body weights, 1 finished session`);
