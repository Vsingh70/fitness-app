export const meta = {
  name: 'body-weight-ui',
  description: 'Build the /body weight-history page + Today tile + body-metrics api/hooks',
  phases: [
    { title: 'Design' },
    { title: 'Implement' },
    { title: 'Verify' },
    { title: 'Fix' },
  ],
}

// ---------------------------------------------------------------------------
// Ground-truth context shared with every agent. This is verified fact gathered
// before the workflow; agents must build to THIS spec, not guess.
// ---------------------------------------------------------------------------
const CONTEXT = `
PROJECT: VGains fitness app. Monorepo. Web app at apps/web (Next.js 15 App Router,
React 19, TanStack Query v5, Zustand, Tailwind v4 with CSS-var tokens, recharts ^3.8.1).
Working dir for all paths below: /Users/vs/Desktop/Code/personal/fitness-app

GOAL: Surface synced body-weight data (from the new Google Health sync) in the web UI.
The backend already has the full REST surface; there is currently NO web UI consuming it.

EXACT BACKEND API (already deployed, do not change):
- GET  /v1/body-metrics?limit=100  -> BodyMetricList { items: BodyMetricResponse[] }
    BodyMetricResponse = { id: string, recorded_at: string(ISO), created_at: string,
      weight_kg: string|null, body_fat_pct: string|null,
      neck_cm: string|null, waist_cm: string|null, hip_cm: string|null }
    (all numeric fields are DECIMAL-AS-STRING or null). Rows are returned newest-first.
- POST /v1/body-metrics  body BodyMetricCreate { recorded_at: string(ISO, REQUIRED),
      weight_kg?: number|string|null, body_fat_pct?: number|string|null,
      waist_cm?, neck_cm?, hip_cm? }  -> BodyMetricResponse
- GET  /v1/body-metrics/trend?weeks=12&window=4 -> BodyMetricTrendResponse
    { weeks: int, window: int, series: BodyMetricTrendSeries[] }
    BodyMetricTrendSeries = { metric: string, points: BodyMetricTrendPoint[] }
    metric is one of: "weight_kg","body_fat_pct","neck_cm","waist_cm","hip_cm"
    BodyMetricTrendPoint = { iso_year:int, iso_week:int, week_start:string(ISO date),
      value: string|null, moving_average: string|null }  (oldest-first, one per week)
- DELETE /v1/body-metrics/{metric_id} -> 204

These schema names exist in apps/web/src/lib/api/types.ts already (regenerated):
components["schemas"]["BodyMetricResponse" | "BodyMetricList" | "BodyMetricCreate"
 | "BodyMetricTrendResponse" | "BodyMetricTrendSeries" | "BodyMetricTrendPoint"].

WEB CONVENTIONS (match these EXACTLY):
- API client: import { api } from "@/lib/api/client". Methods: api.get<T>(path),
  api.post<T>(path, body), api.delete<T>(path). Query params are baked into the path
  string via URLSearchParams: const q=new URLSearchParams(); ... api.get<T>(\`/v1/x?\${q}\`).
  Path vars use encodeURIComponent(). Errors throw ApiError {status,code,message,details}.
- api modules start with "use client" and: import type { components } from "@/lib/api/types";
  type Foo = components["schemas"]["Foo"]; then export plain async functions.
- hooks files start with "use client", import * as api from the api module, use
  useQuery/useMutation/useQueryClient from "@tanstack/react-query". Query keys are
  const-asserted tuples at module scope, e.g. const KEY = ["body-metrics"] as const.
  staleTime ~60_000. Mutations invalidate ["body-metrics"] and ["body-metrics","trend"]
  on success (and optimistic updates where sensible, mirroring lib/hooks/analytics.ts).
- IMPORTANT: lib/hooks/health.ts useSyncHealth() ALREADY invalidates ["body-metrics"]
  on success, so the page must use that exact query-key root so a Health sync refreshes it.
- UI primitives (import from "@/components/ui/..."):
  Button { variant:"primary"|"secondary"|"ghost"|"destructive", size:"sm"|"md"|"lg" } from "@/components/ui/button"
  Card, CardHeader, CardContent from "@/components/ui/card"
  Input (styled <input>) from "@/components/ui/input"
  Sheet { open, onOpenChange, title, children } (vaul bottom-sheet) from "@/components/ui/sheet"
  StatTile { label, value, unit?, trend?, delta? } from "@/components/ui/stat-tile"
  TrendChart { kind:"line"|"bar", data:{date,value,overlay?}[], unit?, height?, primaryLabel?, overlayLabel? } from "@/components/charts/trend-chart"
    -- TrendChart already renders "No data yet." for empty data; data values must be numbers.
  Toast: import { useToastStore } from "@/components/ui/toast";
    const pushToast = useToastStore((s)=>s.push); pushToast({kind:"success"|"error"|"info"|"warning", message});
- User units: const me = useMe().data (from "@/lib/hooks/me"); me.unit_system is "metric"|"imperial".
  Backend stores/returns weight in KG always. For imperial display convert kg*2.20462 -> lb (1 dp);
  on submit convert lb/2.20462 -> kg. body_fat_pct + circumferences are unit-agnostic (% / cm; for
  imperial show cm->in via /2.54 if you show circumferences, but circumferences are OPTIONAL/secondary).
- Page layout convention (see apps/web/src/app/(app)/analytics/page.tsx and (app)/page.tsx):
  client component; root <div className="mx-auto flex max-w-5xl flex-col gap-4">;
  <header> with <h1 className="font-serif text-[32px] font-medium tracking-tight">Title</h1>
  + <p className="text-text-secondary mt-1 text-sm">subtitle</p>; loading/error/empty handled
  per-query with ternaries (isLoading ? "Loading…" : isError ? destructive msg : empty ? msg : content).
  Tokens: border-border, bg-surface-elevated, text-text / text-text-secondary / text-text-tertiary,
  text-accent, text-destructive, rounded-[var(--radius-card)] / [var(--radius-button)].
- Nav: apps/web/src/components/layout/nav-items.ts exports NAV_ITEMS: NavItem[]
  { href, label, icon (lucide-react component), mobileVisible:boolean, tutorialId:string }.
  The mobile tab bar should stay at ~5 items, so a new "Body" item should be mobileVisible:false
  (desktop sidebar only), reachable on mobile via the Today tile. Pick a fitting lucide icon
  (e.g. Scale or Weight or Activity — verify the name exists in lucide-react).
- Today page: apps/web/src/app/(app)/page.tsx. Tiles live in apps/web/src/components/today/*.
  ReadinessTile pattern: props { data: T|undefined, isLoading: boolean }; render "—" / "No data yet"
  when missing; wrapper card uses border-border bg-surface-elevated rounded-[var(--radius-card)] border p-5.
  The top grid is: <div className="grid gap-4 md:grid-cols-[1fr_2fr]"> with ReadinessTile + NutritionStrip.

DELIVERABLE FILES (create/modify exactly these — keep diffs minimal and idiomatic):
  NEW apps/web/src/lib/api/body-metrics.ts        (api module: list, log, delete, trend)
  NEW apps/web/src/lib/hooks/body-metrics.ts      (hooks: useBodyMetrics, useBodyTrend, useLogBodyMetric, useDeleteBodyMetric)
  NEW apps/web/src/lib/utils/format-weight.ts     (kg<->display helpers keyed on unit_system; + a shared relativeDate/formatDate helper for the history list)
  NEW apps/web/src/components/body/weight-trend-card.tsx   (Card: trend chart from /trend weight_kg series, mapped to TrendChart points {date:week_start short, value:Number(moving_average ?? value)})
  NEW apps/web/src/components/body/log-weight-sheet.tsx    (Sheet form: weight required + body_fat optional + date default today; unit-aware; calls useLogBodyMetric; success/error toast)
  NEW apps/web/src/components/body/weight-history-list.tsx (list of BodyMetricResponse rows: date, weight (unit-aware), body-fat if present, delete button w/ confirm)
  NEW apps/web/src/components/today/weight-tile.tsx        (compact Today tile: latest weight + weekly delta; links to /body; "No data yet" empty state)
  NEW apps/web/src/app/(app)/body/page.tsx                 (the page: header, StatTile row [current weight, weekly change, last logged], WeightTrendCard, "Log weight" button -> LogWeightSheet, WeightHistoryList)
  EDIT apps/web/src/components/layout/nav-items.ts         (add Body nav item, mobileVisible:false)
  EDIT apps/web/src/app/(app)/page.tsx                     (add <WeightTile> to the Today layout; fetch via useBodyMetrics; keep the existing top grid balanced)

CONSTRAINTS:
- Do NOT touch any file other than the deliverables. Do NOT run git. Do NOT modify backend, types.ts, or unrelated web files.
- Everything must pass: pnpm exec tsc --noEmit, pnpm lint, pnpm build. Use exact import paths above.
- Numeric API fields are STRINGS — always Number(...) before math/charting; guard null.
- Decimals: display weight to 1 dp. Dates in the history list: format like "Jun 6" (short month + day);
  trend X axis: short "M/d" or "Jun 6" from week_start.
`

phase('Design')
// Panel of 3 independent designs for the trickiest decisions (data mapping, unit
// handling, optimistic-update strategy, page composition), then synthesize.
// NOTE: design agents return FREE-TEXT (no structured schema). An earlier run
// hung here in a StructuredOutput retry loop (the model kept dropping a required
// field). The notes only feed the synthesizer, so plain markdown is strictly
// better — no brittle validation barrier.
const lenses = [
  'Focus on DATA CORRECTNESS: exact mapping of the string/null decimal fields and the /trend series (weight_kg) into StatTile values + TrendChart points, weekly-delta computation, and null-safety. Specify the precise transforms.',
  'Focus on UX & COMPOSITION: page layout, the Today tile, empty/loading/error states, the log-weight Sheet form (validation, unit-aware inputs, default date), and history-list delete-with-confirm. Specify component boundaries.',
  'Focus on STATE & UNITS: TanStack Query keys + cache invalidation that cooperates with useSyncHealth (which invalidates ["body-metrics"]), optimistic add/delete, and the kg<->lb conversion helpers (display + submit). Specify the hooks file API.',
]

const designs = await parallel(
  lenses.map((lens, i) => () =>
    agent(
      `${CONTEXT}\n\nYou are design reviewer #${i + 1}. ${lens}\n\nProduce a concrete, implementable design for ONLY your focus area, consistent with the deliverable file list. Be specific enough to code from. Return a short markdown note: a one-paragraph summary, a bulleted list of concrete decisions (topic -> choice -> why), and a bulleted list of risks. Do NOT call any structured-output tool; just return the markdown text.`,
      { label: `design#${i + 1}`, phase: 'Design' },
    ),
  ),
)

const synth = await agent(
  `${CONTEXT}\n\nThree design notes from focused reviewers follow. Synthesize them into ONE authoritative, self-consistent implementation spec covering ALL deliverable files. Resolve any conflicts, pick concrete names/signatures, and write the precise data transforms (string->number, week_start->axis label, weekly delta, kg<->lb). This spec will be handed to implementers who CANNOT see the design notes — so it must be complete and standalone.\n\nDESIGN NOTES:\n${JSON.stringify(designs.filter(Boolean), null, 2)}`,
  { label: 'synthesize-spec', phase: 'Design' },
)

// ---------------------------------------------------------------------------
phase('Implement')
// Two independent file-groups built in parallel in an isolated worktree each
// would conflict on the shared page.tsx/nav edits, so we instead build the
// self-contained leaf modules in parallel (no shared files), then the page +
// integration edits last in one agent (depends on the leaves' exact exports).
const SHARED = `${CONTEXT}\n\nAUTHORITATIVE SPEC (build to this exactly):\n${synth}\n\nWrite production-ready code with the Write tool to the exact paths. Match surrounding code style. Do not run git. Do not edit files outside your assigned set.`

const GROUP_A = `${SHARED}\n\nYOUR FILES (data + utils layer ONLY):\n- apps/web/src/lib/api/body-metrics.ts\n- apps/web/src/lib/hooks/body-metrics.ts\n- apps/web/src/lib/utils/format-weight.ts\nRead apps/web/src/lib/api/client.ts, apps/web/src/lib/api/analytics.ts, apps/web/src/lib/hooks/analytics.ts, apps/web/src/lib/hooks/me.ts, and apps/web/src/lib/hooks/health.ts FIRST to match the exact client/hook idioms and the ["body-metrics"] query key. Then write the three files. Return the exact exported names + signatures you created.`

const GROUP_B = `${SHARED}\n\nYOUR FILES (presentational components ONLY — assume the data layer from group A exists at @/lib/api/body-metrics, @/lib/hooks/body-metrics, @/lib/utils/format-weight with the names from the spec):\n- apps/web/src/components/body/weight-trend-card.tsx\n- apps/web/src/components/body/log-weight-sheet.tsx\n- apps/web/src/components/body/weight-history-list.tsx\n- apps/web/src/components/today/weight-tile.tsx\nRead apps/web/src/components/charts/trend-chart.tsx, apps/web/src/components/ui/{button,card,input,sheet,stat-tile,toast}.tsx, and apps/web/src/components/today/readiness-tile.tsx FIRST. Then write the four files. Return the exact component names + props you created.`

const [groupA, groupB] = await parallel([
  () => agent(GROUP_A, { label: 'impl:data-layer', phase: 'Implement' }),
  () => agent(GROUP_B, { label: 'impl:components', phase: 'Implement' }),
])

// Integration last: page + nav + Today wiring. Needs the real exports from A & B.
const integration = await agent(
  `${SHARED}\n\nThe data layer and components are now written. Their reported exports:\n--- DATA LAYER ---\n${groupA}\n--- COMPONENTS ---\n${groupB}\n\nYOUR FILES (integration — build the page + wire everything):\n- apps/web/src/app/(app)/body/page.tsx  (NEW)\n- apps/web/src/components/layout/nav-items.ts  (EDIT: add the Body nav item, mobileVisible:false, a valid lucide-react icon, a tutorialId like "nav-body"; keep the array shape + ordering sensible, e.g. after Insights or before Settings)\n- apps/web/src/app/(app)/page.tsx  (EDIT: import WeightTile + useBodyMetrics, render the tile in the Today layout without unbalancing the existing grid; minimal diff)\nRead the CURRENT contents of nav-items.ts and (app)/page.tsx with Read BEFORE editing, and use Edit for the two existing files (minimal diffs) and Write for the new page. Verify the lucide icon name actually exists. Return a summary of what you changed.`,
  { label: 'impl:integration', phase: 'Implement' },
)

// ---------------------------------------------------------------------------
phase('Verify')
// Adversarial review: 3 independent reviewers, each a distinct lens, each told
// to assume the code is BROKEN and find concrete defects. Plus a hard gate of
// the actual tooling is run by the parent AFTER the workflow (tsc/lint/build),
// so reviewers focus on correctness the compiler can't catch.
const REVIEW_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['file', 'severity', 'issue', 'fix'],
        properties: {
          file: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          issue: { type: 'string' },
          fix: { type: 'string' },
        },
      },
    },
  },
}

const reviewLenses = [
  'TYPES & COMPILE: read every new/edited file and find anything that will fail `tsc --noEmit` or `next lint`: wrong import paths, missing "use client", untyped any, components["schemas"] names that do not exist in types.ts, recharts prop misuse, unused vars, missing keys in lists. Verify the lucide-react icon name actually exists.',
  'DATA CORRECTNESS: verify every string|null decimal is Number()-guarded before math/charting; the weekly-delta sign/direction is correct; the /trend "weight_kg" series is the one selected and mapped to TrendChart {date,value} with null points dropped or zeroed sensibly; kg<->lb conversion is correct both directions and only applied to weight (not %); date formatting handles ISO strings.',
  'INTEGRATION & STATE: verify query keys exactly match ["body-metrics"] root so useSyncHealth invalidation refreshes the page; optimistic add/delete rollback on error; the Today page edit does not break the existing grid or remove existing tiles; nav-items edit keeps the NavItem shape and mobile tab count sane; the Sheet open/close + form reset works; no duplicate/again-fetch loops.',
]

const reviews = await parallel(
  reviewLenses.map((lens, i) => () =>
    agent(
      `${CONTEXT}\n\nReview the IMPLEMENTED feature. Assume it is broken and find concrete, real defects (cite file + line/snippet). ${lens}\n\nOnly report defects you can substantiate by reading the actual files. If a file is correct, do not invent issues. Read all deliverable files as needed.`,
      { label: `review#${i + 1}`, phase: 'Verify', schema: REVIEW_SCHEMA },
    ),
  ),
)

const allFindings = reviews.filter(Boolean).flatMap((r) => r.findings || [])
const blockers = allFindings.filter((f) => f.severity === 'blocker' || f.severity === 'major')

// ---------------------------------------------------------------------------
phase('Fix')
let fixSummary = 'No blocker/major findings — nothing to fix.'
if (blockers.length > 0) {
  fixSummary = await agent(
    `${CONTEXT}\n\nReviewers found these blocker/major defects in the implemented feature. Fix EACH one by editing the offending file (Read it first, then Edit). Do not introduce regressions; keep diffs minimal. Do not run git.\n\nDEFECTS:\n${JSON.stringify(blockers, null, 2)}\n\nReturn a concise list of what you changed per file.`,
    { label: 'apply-fixes', phase: 'Fix' },
  )
}

return {
  spec: synth,
  integration,
  totalFindings: allFindings.length,
  blockers: blockers.length,
  findings: allFindings,
  fixSummary,
}
