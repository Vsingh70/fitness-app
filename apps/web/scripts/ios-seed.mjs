// Seeds the iOS app's DEBUG dev user (sub "ios-dev-user") with a distinctively-named
// active program so the wired iOS app shows real server data. Run: node scripts/ios-seed.mjs
const API = "http://127.0.0.1:8000";
async function api(method, path, token, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.status === 204 ? null : res.json();
}
const tryApi = (m, p, t, b) => api(m, p, t, b).catch((e) => { console.warn("  !", String(e.message).slice(0, 120)); return null; });

const tok = (await api("POST", "/v1/auth/dev", null, { sub: "ios-dev-user", email: "ios-dev-user@example.com" })).access_token;
console.log("• signed in ios-dev-user");
const list = (await tryApi("GET", "/v1/exercises?limit=50", tok)) || { items: [] };
const ex = (i) => list.items[i % list.items.length]?.id;

// Clean any prior ios-dev programs so the seed is deterministic.
const existing = (await tryApi("GET", "/v1/programs?limit=100", tok)) || { items: [] };
for (const p of existing.items || []) await tryApi("DELETE", `/v1/programs/${p.id}`, tok);

const prog = await api("POST", "/v1/programs", tok, { name: "Live Wired ✓", description: "Fetched from the API", goal: "hypertrophy" });
let n = 0;
for (const [name, rest] of [["Push", false], ["Pull", false], ["Legs", false], ["Rest", true], ["Upper", false], ["Lower", false], ["Rest", true]]) {
  const s = await api("POST", `/v1/programs/${prog.id}/slots`, tok, { name, is_rest_day: rest });
  if (!rest && list.items.length) for (let k = 0; k < 4; k++)
    await tryApi("POST", `/v1/program-slots/${s.id}/exercises`, tok, { exercise_id: ex(n++), target_sets: 4, target_reps_low: 8, target_reps_high: 12, rest_seconds: 120, rep_mode: "range" });
}
await tryApi("PATCH", `/v1/programs/${prog.id}`, tok, { periodization_mode: "block", mesocycle_length_microcycles: 4, auto_deload: true, intensity_mode: "rpe" });
await tryApi("POST", `/v1/programs/${prog.id}/activate`, tok, null);
for (let i = 0; i < 6; i++) await tryApi("POST", `/v1/programs/${prog.id}/advance`, tok, null);
console.log(`• seeded + activated "Live Wired ✓" (${prog.id}) for ios-dev-user`);
