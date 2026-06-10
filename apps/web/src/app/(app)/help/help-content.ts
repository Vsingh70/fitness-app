/**
 * Per-page help content for the Help & Guide page. One concise block per screen:
 * what it's for, the key things you can do, and one concrete worked example.
 */

export interface HelpSection {
  id: string;
  page: string;
  href: string;
  whatItsFor: string;
  keyActions: string[];
  example: { title: string; steps: string[] };
}

export const HELP_SECTIONS: HelpSection[] = [
  {
    id: "today",
    page: "Today",
    href: "/",
    whatItsFor:
      "Your daily home base. It shows what's scheduled for today, how your nutrition is tracking, smart recommendations, and your recent sessions — so you can start training in one tap.",
    keyActions: [
      "Tap Start workout to begin an empty session right away.",
      "See your kcal + macro rings update as you eat through the day.",
      "Open a recommendation card to act on what to push next.",
      "Jump into a scheduled workout if your active program has one today.",
    ],
    example: {
      title: "Start training in 10 seconds",
      steps: [
        "Open Today.",
        "Tap Start workout to create a fresh session.",
        "Add an exercise and log your first set — you're training.",
      ],
    },
  },
  {
    id: "workouts",
    page: "Workouts",
    href: "/workouts",
    whatItsFor:
      "Your full training history, newest first, grouped by week. Open any session to log sets live — weight, reps, RPE — run the rest timer, and see personal records when you finish.",
    keyActions: [
      "Open a session to log sets; use the rest timer between sets.",
      "Press ? inside a session for keyboard shortcuts (e, n, j/k, r).",
      "Finish a session to see your summary, volume, and any PRs.",
      "Use the calendar view to see sessions laid out by date.",
    ],
    example: {
      title: "Log a bench press set",
      steps: [
        "Open a session and add Barbell Bench Press.",
        "Enter 80 kg × 8 reps, RPE 8, then save the set.",
        "Hit the rest timer and let it count down before your next set.",
      ],
    },
  },
  {
    id: "programs",
    page: "Programs",
    href: "/programs",
    whatItsFor:
      "Pick a ready-made template or design your own training split. When you activate a program, VGains schedules your training days for you so Today and the calendar know what's next.",
    keyActions: [
      "Browse templates by goal (hypertrophy, strength, powerbuilding).",
      "Tap New program to build a split from scratch.",
      "Add days and assign exercises with set/rep schemes.",
      "Activate a program and choose a start date.",
    ],
    example: {
      title: "Run a Push/Pull/Legs split",
      steps: [
        "Open Programs and pick a PPL template (or tap New program).",
        "Review the days and exercises, adjusting sets if you like.",
        "Tap Activate and choose today as the start date.",
      ],
    },
  },
  {
    id: "nutrition",
    page: "Nutrition",
    href: "/nutrition",
    whatItsFor:
      "Track what you eat against your daily calorie and macro targets. Log foods into Breakfast, Lunch, Dinner, or Snack by searching a food database — totals fill in as you add.",
    keyActions: [
      "Tap + Add on a meal to search for a food.",
      "Pick a food and enter grams to log it.",
      "Watch the macro rings move toward your targets.",
      "Remove an item with the trash icon if you mis-logged.",
    ],
    example: {
      title: "Log a chicken-and-rice lunch",
      steps: [
        "Open Nutrition and tap + Add on Lunch.",
        "Search 'chicken breast', pick it, enter 200 g.",
        "Add 'white rice' at 150 g — your protein and carb rings jump.",
      ],
    },
  },
  {
    id: "insights",
    page: "Insights",
    href: "/analytics",
    whatItsFor:
      "See your training trends over time: weekly set volume, tonnage charts, and a per-muscle heatmap showing what you've trained. Auto-generated insight cards flag what to push or ease off.",
    keyActions: [
      "Check sets/week and tonnage to gauge your workload.",
      "Read the muscle heatmap to spot under-trained areas.",
      "Review weekly insight cards for actionable feedback.",
      "Dismiss an insight once you've acted on it.",
    ],
    example: {
      title: "Find a lagging muscle group",
      steps: [
        "Open Insights and look at the muscle heatmap.",
        "Spot a muscle that's cool (low volume) this week.",
        "Add an exercise for it to your next session or program day.",
      ],
    },
  },
  {
    id: "settings",
    page: "Settings",
    href: "/settings",
    whatItsFor:
      "Make VGains yours. Set your theme and accent color, switch between kg and lb, manage your active program and default rest timer, and connect Fitbit (via Google).",
    keyActions: [
      "Switch theme (light/auto/dark) and accent color live.",
      "Choose kg/lb and km/mi units.",
      "Set your default rest-timer length.",
      "Connect Fitbit (via Google) to sync weight, body fat, and recovery metrics.",
    ],
    example: {
      title: "Switch to pounds and a dark theme",
      steps: [
        "Open Settings → Units & defaults and choose lb.",
        "Go to Appearance and pick Dark.",
        "Pick an accent color — the whole app re-themes instantly.",
      ],
    },
  },
];
