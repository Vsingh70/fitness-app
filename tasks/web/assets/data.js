// Shared mock data — consistent fake user across every screen.
// Alex Chen, intermediate lifter, week 4/8 of PPL — Vanilla 6-day.

window.MOCK = {
  user: {
    name: "Alex Chen",
    initials: "AC",
    email: "alex@chen.fyi",
    units: "kg",
    accent: "blue",
    timezone: "America/Los_Angeles",
    bodyweight_kg: 78.4,
    bodyweight_lb: 172.8,
    age: 31,
  },
  program: {
    name: "PPL — Vanilla 6-day",
    goal: "hypertrophy",
    progression: "double_progression",
    weeks: 8,
    current_week: 4,
    days_per_week: 6,
    next_day: "Push A",
    next_exercise_count: 5,
    next_estimated_min: 58,
  },
  readiness: {
    score: 78,
    band: "high",
    sleep_hours: 7.4,
    rhr: 56,
    hrv_ms: 64,
    delta_vs_7d: +6,
  },
  today: "Tuesday, May 27",
  // Sample set history for Bench Press, week-over-week
  bench: {
    name: "Barbell Bench Press",
    primary: "chest",
    secondary: ["triceps", "front_delts"],
    equipment: "barbell",
    tracking: "weight_reps",
    e1rm: 112.5,
    e1rm_delta_4w: +4.5,
    best_set: { weight: 100, reps: 5, date: "May 13" },
    last_session: [
      { weight: 60, reps: 8, set_type: "warmup" },
      { weight: 80, reps: 5, set_type: "warmup" },
      { weight: 92.5, reps: 8, rpe: 7.5 },
      { weight: 92.5, reps: 8, rpe: 8 },
      { weight: 92.5, reps: 7, rpe: 9 },
      { weight: 85, reps: 9, rpe: 9, set_type: "backoff" },
    ],
  },
  // Active session in progress (used for workout-active.html)
  active_session: {
    id: "ws-2026-05-27-pushA",
    name: "Push A — Week 4",
    started_at_iso: "2026-05-27T17:42:00",
    program_day: "Push A",
    exercises: [
      {
        id: "we-1",
        name: "Barbell Bench Press",
        muscle: "chest",
        equipment: "barbell",
        target: "4 × 6–8 @ RPE 8",
        rest_sec: 180,
        tracking: "weight_reps",
        previous: [
          { weight: 90, reps: 8 }, { weight: 90, reps: 8 }, { weight: 90, reps: 7 }, { weight: 90, reps: 6 },
        ],
        sets: [
          { id: "s1", weight: 92.5, reps: 8, rpe: 7.5, done: true, synced: true },
          { id: "s2", weight: 92.5, reps: 8, rpe: 8, done: true, synced: true },
          { id: "s3", weight: 92.5, reps: 0, rpe: 0, done: false, synced: false },
          { id: "s4", weight: 92.5, reps: 0, rpe: 0, done: false, synced: false },
        ],
      },
      {
        id: "we-2",
        name: "Overhead Press",
        muscle: "front_delts",
        equipment: "barbell",
        target: "4 × 8–10 @ RPE 8",
        rest_sec: 150,
        tracking: "weight_reps",
        previous: [{ weight: 52.5, reps: 10 }, { weight: 52.5, reps: 9 }, { weight: 52.5, reps: 8 }, { weight: 52.5, reps: 7 }],
        sets: [
          { id: "s5", weight: 55, reps: 0, rpe: 0, done: false, synced: false },
          { id: "s6", weight: 55, reps: 0, rpe: 0, done: false, synced: false },
          { id: "s7", weight: 55, reps: 0, rpe: 0, done: false, synced: false },
          { id: "s8", weight: 55, reps: 0, rpe: 0, done: false, synced: false },
        ],
      },
      {
        id: "we-3",
        name: "Incline DB Press",
        muscle: "chest",
        equipment: "dumbbell",
        target: "3 × 10–12",
        rest_sec: 120,
        tracking: "weight_reps",
        previous: [{ weight: 32, reps: 12 }, { weight: 32, reps: 11 }, { weight: 32, reps: 10 }],
        sets: [
          { id: "s9", weight: 0, reps: 0, rpe: 0, done: false, synced: false },
          { id: "s10", weight: 0, reps: 0, rpe: 0, done: false, synced: false },
          { id: "s11", weight: 0, reps: 0, rpe: 0, done: false, synced: false },
        ],
      },
      {
        id: "we-4",
        name: "Cable Lateral Raise",
        muscle: "side_delts",
        equipment: "cable",
        target: "3 × 12–15",
        rest_sec: 90,
        tracking: "weight_reps",
        previous: [{ weight: 14, reps: 15 }, { weight: 14, reps: 13 }, { weight: 14, reps: 12 }],
        sets: [
          { id: "s12", weight: 0, reps: 0, rpe: 0, done: false, synced: false },
          { id: "s13", weight: 0, reps: 0, rpe: 0, done: false, synced: false },
          { id: "s14", weight: 0, reps: 0, rpe: 0, done: false, synced: false },
        ],
      },
      {
        id: "we-5",
        name: "Rope Triceps Pushdown",
        muscle: "triceps",
        equipment: "cable",
        target: "3 × 12–15",
        rest_sec: 75,
        tracking: "weight_reps",
        previous: [{ weight: 32, reps: 15 }, { weight: 32, reps: 14 }, { weight: 32, reps: 12 }],
        sets: [
          { id: "s15", weight: 0, reps: 0, rpe: 0, done: false, synced: false },
          { id: "s16", weight: 0, reps: 0, rpe: 0, done: false, synced: false },
          { id: "s17", weight: 0, reps: 0, rpe: 0, done: false, synced: false },
        ],
      },
    ],
  },
  // Volume rollups for analytics
  volume_week: {
    chest:       { sets: 14, target: 14, change: +2 },
    lats:        { sets: 16, target: 16, change: 0 },
    mid_back:    { sets: 8,  target: 10, change: -2 },
    lower_back:  { sets: 4,  target: 6,  change: 0 },
    traps:       { sets: 6,  target: 8,  change: +1 },
    rear_delts:  { sets: 5,  target: 9,  change: -1 },
    side_delts:  { sets: 9,  target: 9,  change: 0 },
    front_delts: { sets: 11, target: 9,  change: +3 },
    biceps:      { sets: 12, target: 12, change: 0 },
    triceps:     { sets: 13, target: 12, change: +1 },
    forearms:    { sets: 2,  target: 4,  change: 0 },
    abs:         { sets: 6,  target: 8,  change: +2 },
    obliques:    { sets: 2,  target: 4,  change: 0 },
    glutes:      { sets: 14, target: 14, change: 0 },
    quads:       { sets: 18, target: 16, change: +2 },
    hamstrings:  { sets: 10, target: 12, change: -1 },
    adductors:   { sets: 0,  target: 4,  change: 0 },
    abductors:   { sets: 0,  target: 4,  change: 0 },
    calves:      { sets: 6,  target: 8,  change: +1 },
  },
  // Weekly insights (3-6 cards)
  insights: [
    { kind: "pr_streak", severity: "info", title: "Three PRs this week", body: "Bench, overhead press, and Bulgarian split squat all moved up. Keep the current rep ranges for one more week." },
    { kind: "plateau", severity: "notice", title: "Pull-ups stuck at 9 reps", body: "Three sessions at 9 reps. Try a deload to bodyweight only, or add 1 reset rest-pause set." },
    { kind: "imbalance", severity: "notice", title: "Rear delts under-trained", body: "5 sets vs target 9. Add a face-pull superset to Pull day." },
    { kind: "under_recovered", severity: "warning", title: "Sleep dipped this week", body: "Average 6.4 h vs your 7.5 h baseline. Consider moving leg day one day later." },
  ],
  // Recommendations cards on Today
  recs: [
    {
      kind: "add_weight", confidence: "high", exercise: "Barbell Bench Press",
      title: "Add 2.5 kg to bench",
      rationale: "8 / 8 / 7 @ RPE 7.5–9 last session. Top of range.", cta: "Apply to today",
    },
    {
      kind: "extra_rest", confidence: "medium", exercise: "Bulgarian Split Squat",
      title: "Try 30 s more rest", rationale: "Reps dropped >2 from set 1 to set 3.", cta: "Tap to learn why",
    },
    {
      kind: "swap_exercise", confidence: "low", exercise: "Pull-Up",
      title: "Consider lat pulldown",
      rationale: "Three sessions stuck at 9 reps.", cta: "Tap to learn why",
    },
  ],
  // Last 7 completed sessions
  recent_sessions: [
    { date: "Mon May 26", day: "Legs A", duration: "1:08", sets: 22, prs: 1, volume_kg: 6480 },
    { date: "Sat May 24", day: "Pull A", duration: "0:55", sets: 19, prs: 0, volume_kg: 4220 },
    { date: "Fri May 23", day: "Push A", duration: "0:58", sets: 21, prs: 2, volume_kg: 5125 },
    { date: "Wed May 21", day: "Legs B", duration: "1:12", sets: 24, prs: 0, volume_kg: 6740 },
    { date: "Tue May 20", day: "Pull B", duration: "0:54", sets: 20, prs: 1, volume_kg: 4380 },
    { date: "Mon May 19", day: "Push B", duration: "0:51", sets: 19, prs: 0, volume_kg: 4710 },
    { date: "Sat May 17", day: "Legs A", duration: "1:05", sets: 22, prs: 0, volume_kg: 6320 },
  ],
  // Nutrition target + today
  nutrition: {
    target: { kcal: 2680, protein_g: 200, carbs_g: 300, fat_g: 80, fiber_g: 35 },
    today: { kcal: 1620, protein_g: 134, carbs_g: 168, fat_g: 51, fiber_g: 22 },
    meals: [
      { type: "breakfast", at: "07:30", items: [
        { name: "Oats, rolled", brand: "Bob's Red Mill", grams: 80, kcal: 304, p: 11, c: 54, f: 5, source: "usda" },
        { name: "Whey isolate", brand: "Optimum", grams: 30, kcal: 117, p: 24, c: 2, f: 1, source: "barcode" },
        { name: "Blueberries", grams: 120, kcal: 69, p: 1, c: 17, f: 0, source: "usda" },
      ]},
      { type: "lunch", at: "12:45", items: [
        { name: "Chicken thigh, grilled", grams: 200, kcal: 410, p: 52, c: 0, f: 22, source: "photo" },
        { name: "Jasmine rice, cooked", grams: 180, kcal: 234, p: 5, c: 51, f: 0, source: "usda" },
        { name: "Mixed greens + olive oil", grams: 90, kcal: 116, p: 1, c: 4, f: 11, source: "manual" },
      ]},
      { type: "dinner", at: "—", items: [] },
      { type: "snack", at: "15:10", items: [
        { name: "Greek yogurt, 2%", grams: 200, kcal: 130, p: 17, c: 9, f: 4, source: "barcode" },
        { name: "Honey", grams: 15, kcal: 46, p: 0, c: 12, f: 0, source: "manual" },
      ]},
    ],
  },
  // Strong / weak point summaries
  strong_weak: [
    { kind: "strong", muscle: "chest", note: "Top decile vs your peers", icon: "trending_up" },
    { kind: "strong", muscle: "quads", note: "Above bodyweight ratio target", icon: "trending_up" },
    { kind: "weak", muscle: "rear_delts", note: "Under target 4 of last 6 weeks", icon: "trending_down" },
    { kind: "weak", muscle: "hamstrings", note: "Ratio 0.42 vs quads (target 0.65)", icon: "trending_down" },
  ],
  // Calendar — current month (May 2026 for the demo). Each cell either logged, planned, rest.
  calendar_days: (() => {
    // May 2026 starts on Friday. 31 days.
    const days = [];
    const planned = { 1: "Push A", 2: "Legs A", 4: "Pull A", 5: "Push B", 6: "Legs B", 8: "Pull B", 9: "Push A",
      11: "Legs A", 12: "Pull A", 13: "Push B", 15: "Legs B", 16: "Pull B", 17: "Push A", 19: "Push B",
      20: "Pull B", 21: "Legs B", 23: "Push A", 24: "Pull A", 26: "Legs A", 27: "Push A", 28: "Pull A",
      30: "Push B", 31: "Legs B" };
    const completed = { 1: true, 2: true, 4: true, 5: true, 6: true, 8: true, 9: true, 11: true, 12: true,
      13: true, 15: true, 16: true, 17: true, 19: true, 20: true, 21: true, 23: true, 24: true, 26: true };
    for (let d = 1; d <= 31; d++) {
      const has = planned[d];
      days.push({
        d, day: has || null,
        completed: completed[d] || false,
        today: d === 27,
        future: d > 27,
      });
    }
    return days;
  })(),
};

// Small helpers
window.kgToLb = (kg) => Math.round(kg * 2.20462 * 10) / 10;
window.unitWeight = (kg) => {
  const u = (localStorage.getItem("om.units") || "kg");
  if (u === "lb") return { val: window.kgToLb(kg).toFixed(1), unit: "lb" };
  return { val: Number.isInteger(kg) ? kg.toString() : kg.toFixed(1), unit: "kg" };
};
