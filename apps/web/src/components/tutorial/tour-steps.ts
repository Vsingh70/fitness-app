/**
 * Onboarding spotlight-tour steps. Each step highlights a real element on the
 * Today screen (identified by `data-tutorial="<target>"`) and explains it.
 *
 * The nav targets (nav-today, nav-workouts, …) are present in both the desktop
 * sidebar and the mobile tab bar, so the tour works at any viewport — it spots
 * whichever copy is visible. A null target renders a centered card (intro/outro).
 */

export interface TourStep {
  /** data-tutorial value of the element to spotlight, or null for a centered card. */
  target: string | null;
  title: string;
  body: string;
}

export const TOUR_STEPS: TourStep[] = [
  {
    target: null,
    title: "Welcome to VGains",
    body: "A quick 60-second tour of the six places you'll use most. You can skip anytime, and replay this from Help.",
  },
  {
    target: "nav-today",
    title: "Today",
    body: "Your home base. See today's scheduled workout, your nutrition rings, smart recommendations, and recent sessions — then jump straight into training.",
  },
  {
    target: "nav-workouts",
    title: "Workouts",
    body: "Every session you've logged, newest first. Open one to log sets, weight, reps and RPE, run the rest timer, and see PRs when you finish.",
  },
  {
    target: "nav-programs",
    title: "Programs",
    body: "Pick a ready-made template or build your own split. Activate a program and it schedules your training days for you.",
  },
  {
    target: "nav-nutrition",
    title: "Nutrition",
    body: "Log meals by searching a food database. Your calories and macros fill in against your daily targets as you go.",
  },
  {
    target: "nav-insights",
    title: "Insights",
    body: "Trends over time — weekly volume, a per-muscle heatmap, and tonnage charts — plus auto-generated insights on what to push or ease off.",
  },
  {
    target: "nav-settings",
    title: "Settings",
    body: "Make it yours: theme and accent color, kg/lb units, your active program, and connections like Fitbit.",
  },
  {
    target: null,
    title: "You're set",
    body: "That's the tour. The fastest way to start: open Today and tap Start workout. Need this again? Open Help from anywhere.",
  },
];
