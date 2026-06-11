export const meta = {
  name: 'health-phase-d',
  description: 'Build /health page + Today steps/sleep tiles + readiness daily-metrics UI',
  phases: [
    { title: 'Design' },
    { title: 'Implement' },
    { title: 'Verify' },
    { title: 'Fix' },
  ],
}

const CTX = `
VGains web app: /Users/vs/Desktop/Code/personal/fitness-app/apps/web (Next.js 15 App Router, React 19, TanStack Query v5, Tailwind v4 CSS-var tokens, recharts ^3.8.1).
GOAL (Phase D): surface the watch's daily metrics — STEPS, SLEEP, RESTING HR, HRV — now syncing into the backend. Two surfaces: (1) compact tiles on the Today dashboard, (2) a dedicated /health page with trends. The readiness tile already exists and is auto-fed; do NOT rebuild it.

EXACT API (already deployed; types in apps/web/src/lib/api/types.ts after regen):
- GET /v1/readiness/today -> ReadinessTodayResponse { date:string, score:int|null, band:"low"|"moderate"|"high"|null, has_data:bool }
- GET /v1/readiness/history?from=YYYY-MM-DD&to=YYYY-MM-DD -> ReadinessHistoryResponse { items: ReadinessDay[] }
    ReadinessDay = { date:string, score:int|null, band:"low"|"moderate"|"high"|null, steps:int|null, sleep_minutes:int|null, resting_hr:int|null, hrv_ms:string|null }
    (hrv_ms is a DECIMAL-as-STRING; the rest are ints or null. Range max 365 days; the 'to' date must be >= the 'from' date. 400 if invalid.)
  components["schemas"]["ReadinessTodayResponse" | "ReadinessHistoryResponse" | "ReadinessDay"] all exist.

WEB CONVENTIONS — match these EXACTLY (read the files):
- API client: import { api } from "@/lib/api/client". api.get<T>(path) with query params baked into the path via URLSearchParams (see apps/web/src/lib/api/today.ts + analytics.ts). api.get<ReadinessHistoryResponse>(\`/v1/readiness/history?\${q}\`).
- api modules: "use client"; import type { components } from "@/lib/api/types"; type Foo = components["schemas"]["Foo"]; export plain async fns. See apps/web/src/lib/api/today.ts (has getReadinessToday already) + apps/web/src/lib/api/body-metrics.ts (the weight feature — the CLOSEST template).
- hooks: "use client"; useQuery/useMutation; const-tuple query keys at module scope; staleTime ~60_000. See apps/web/src/lib/hooks/today.ts (has useReadinessToday, key ["readiness","today"]) + apps/web/src/lib/hooks/body-metrics.ts.
- UI primitives: Button "@/components/ui/button"; Card/CardHeader/CardContent "@/components/ui/card"; StatTile {label,value,unit?,trend?:"up"|"down"|"flat",delta?} "@/components/ui/stat-tile" (delta block renders only when BOTH trend AND delta set; up=success/green, down=destructive/red, flat=grey); TrendChart {kind:"line"|"bar", data:{date:string,value:number,overlay?:number}[], unit?, height?, primaryLabel?, overlayLabel?} "@/components/charts/trend-chart" (renders "No data yet." when empty; values must be NUMBERS).
- Today tile pattern: apps/web/src/components/today/readiness-tile.tsx + weight-tile.tsx — props { data: T|undefined, isLoading: boolean }; render "—"/"No data yet" when missing; card classes border-border bg-surface-elevated rounded-[var(--radius-card)] border p-5. The Today page apps/web/src/app/(app)/page.tsx top grid currently:
    <div className="grid gap-4 md:grid-cols-[1fr_2fr]">
      <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-1">
        <ReadinessTile .../>
        <WeightTile .../>
      </div>
      <NutritionStrip .../>
    </div>
- The /body page (apps/web/src/app/(app)/body/page.tsx) is the CLOSEST page template: header, StatTile row, trend Card, layout, loading/error/empty. MIRROR its structure for /health.
- format helpers exist in apps/web/src/lib/utils/format-weight.ts (toNum, round1, formatShortDate, relativeDate). Reuse toNum/formatShortDate. Add a small format-health.ts ONLY if you need sleep-minutes->"7h 24m" + step formatting (e.g. "12,438") + hrv/hr formatting — keep it tiny.
- Units: steps/sleep/HR/HRV are unit-agnostic (no kg/lb concern). Sleep shown as "Xh Ym" from minutes. Steps with thousands separators.
- Nav: apps/web/src/components/layout/nav-items.ts NAV_ITEMS. There is ALREADY a "Body" item (Scale icon, mobileVisible:false). ADD a "Health" item (mobileVisible:false, a valid lucide-react icon like Activity or HeartPulse — VERIFY it exists in lucide-react; tutorialId "nav-health"). Keep mobile tab bar count sane (these are desktop-sidebar only).

DELIVERABLES (create/modify; tight idiomatic diffs):
  NEW apps/web/src/lib/api/readiness.ts          (getReadinessHistory(params:{from,to}) -> ReadinessHistoryResponse; re-export getReadinessToday or import from today.ts — pick one, don't duplicate the path string)
  NEW apps/web/src/lib/hooks/readiness.ts        (useReadinessHistory(days=30) computing from/to client-side; key ["readiness","history",{days}]; staleTime 60_000)
  NEW apps/web/src/lib/utils/format-health.ts    (formatSleep(minutes:int|null)->"7h 24m"|"—"; formatSteps(n:int|null)->"12,438"|"—"; passthrough formatters for HR "54 bpm"/HRV "48 ms")
  NEW apps/web/src/components/today/steps-tile.tsx  (compact Today tile: today's steps + a tiny context like "vs 7-day avg"; "No data yet" empty; links to /health)
  NEW apps/web/src/components/today/sleep-tile.tsx  (compact Today tile: last night's sleep "7h 24m"; "No data yet" empty; links to /health)
  NEW apps/web/src/components/health/metric-trend-card.tsx (reusable Card wrapping TrendChart for one metric: title, unit, maps ReadinessDay[] -> {date:formatShortDate, value:Number}; drops null points; isLoading/isError states)
  NEW apps/web/src/app/(app)/health/page.tsx     (the page: header "Health"; StatTile row [latest steps, last sleep, resting HR, HRV]; then MetricTrendCards for steps / sleep(hours or minutes) / resting HR / HRV over ~30 days from /readiness/history; loading/error/empty per query)
  EDIT apps/web/src/components/layout/nav-items.ts  (add Health nav item)
  EDIT apps/web/src/app/(app)/page.tsx           (add StepsTile + SleepTile to the Today layout; fetch via the new hooks (or reuse useReadinessHistory for the 7-day context + today's value); keep the existing grid balanced — the left column currently stacks ReadinessTile+WeightTile; integrate steps/sleep without breaking it. Minimal diff. Read the file first.)

DATA NOTES:
- "Today's steps" / "last night's sleep" = the most recent ReadinessDay with a non-null value (history is returned; pick latest). hrv_ms is a STRING -> Number() before charting; guard null. Steps SUM already done server-side (one value per day). Sleep trend can be shown in HOURS (minutes/60, 1dp) or minutes — pick hours for readability, label "h".
- resting HR trend: lower is better, but just show the line; don't over-engineer trend direction.

CONSTRAINTS:
- Must pass: pnpm exec tsc --noEmit ; pnpm lint ; pnpm format:check ; pnpm build. Use exact import paths. Numeric-string fields -> Number()/toNum guarded. No new deps.
- Do NOT touch the backend, types.ts (already regenerated), readiness-tile.tsx, or unrelated files. Do NOT run git.
- VERIFY any lucide-react icon name actually exists before using it.
`

phase('Design')
const design = await agent(
  `${CTX}\n\nProduce ONE concrete, standalone implementation spec for ALL deliverable files: exact exported names/signatures, the ReadinessDay->TrendChart point mapping, the latest-value + 7-day-avg computations, sleep minutes->"Xh Ym", the Today-layout integration (how steps/sleep tiles slot in without unbalancing the grid), and the chosen lucide icon (name you verified plausible). Implementers will NOT see this prompt's nuance beyond the spec, so be complete. Return markdown only; do not call any tool.`,
  { label: 'design', phase: 'Design' },
)

phase('Implement')
const SHARED = `${CTX}\n\nAUTHORITATIVE SPEC:\n${design}\n\nWrite production code with Write/Edit to the exact paths. Match surrounding style. Do not run git. Do not edit files outside your set.`

const [dataLayer, components] = await parallel([
  () => agent(`${SHARED}\n\nYOUR FILES (data/utils ONLY):\n- apps/web/src/lib/api/readiness.ts\n- apps/web/src/lib/hooks/readiness.ts\n- apps/web/src/lib/utils/format-health.ts\nRead apps/web/src/lib/api/today.ts, apps/web/src/lib/hooks/today.ts, apps/web/src/lib/api/body-metrics.ts, apps/web/src/lib/utils/format-weight.ts FIRST. Return exact exported names + signatures.`, { label: 'impl:data', phase: 'Implement' }),
  () => agent(`${SHARED}\n\nYOUR FILES (presentational, assume data layer exists at @/lib/api/readiness, @/lib/hooks/readiness, @/lib/utils/format-health per the spec):\n- apps/web/src/components/health/metric-trend-card.tsx\n- apps/web/src/components/today/steps-tile.tsx\n- apps/web/src/components/today/sleep-tile.tsx\nRead apps/web/src/components/charts/trend-chart.tsx, apps/web/src/components/ui/{button,card,stat-tile}.tsx, apps/web/src/components/today/{readiness-tile,weight-tile}.tsx FIRST. Return exact component names + props.`, { label: 'impl:components', phase: 'Implement' }),
])

const integration = await agent(
  `${SHARED}\n\nData layer + components are written. Reported exports:\n--- DATA ---\n${dataLayer}\n--- COMPONENTS ---\n${components}\n\nYOUR FILES (integration):\n- apps/web/src/app/(app)/health/page.tsx (NEW — mirror apps/web/src/app/(app)/body/page.tsx structure)\n- apps/web/src/components/layout/nav-items.ts (EDIT: add Health item, mobileVisible:false, verified lucide icon, tutorialId "nav-health")\n- apps/web/src/app/(app)/page.tsx (EDIT: add StepsTile + SleepTile to Today; minimal diff; keep grid balanced)\nRead the CURRENT body/page.tsx, nav-items.ts, and (app)/page.tsx with Read BEFORE writing/editing. Use Edit (minimal) for the 2 existing files, Write for the new page. Verify the lucide icon exists. Return what you changed.`,
  { label: 'impl:integration', phase: 'Implement' },
)

phase('Verify')
const REVIEW_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['findings'],
  properties: { findings: { type: 'array', items: {
    type: 'object', additionalProperties: false,
    required: ['file', 'severity', 'issue', 'fix'],
    properties: { file: {type:'string'}, severity: {type:'string', enum:['blocker','major','minor']}, issue: {type:'string'}, fix: {type:'string'} },
  } } },
}
const lenses = [
  'TYPES/COMPILE: read every new/edited file; find anything failing tsc/lint/build: wrong import paths, missing "use client", components["schemas"] names not in types.ts, recharts misuse, unused vars, missing list keys, a lucide-react icon name that does not exist.',
  'DATA: hrv_ms (string) Number()-guarded before charting; null points dropped; latest-value = most recent non-null day; sleep minutes->"Xh Ym" correct; steps thousands-format; ReadinessDay->TrendChart {date,value} mapping correct; from/to date range built correctly (<=365d, to>=from).',
  'INTEGRATION: Today grid stays balanced + existing tiles intact; nav-items keeps NavItem shape + mobile count sane; /health page mirrors /body conventions (loading/error/empty); query keys sane; no duplicate path strings between readiness.ts and today.ts.',
]
const reviews = await parallel(lenses.map((lens,i)=>()=>agent(`${CTX}\n\nThe feature is implemented. Adversarially review — assume bugs, find concrete real defects by READING the files. ${lens}\n\nOnly substantiated defects (cite file+snippet). Empty findings if clean.`, {label:`review#${i+1}`, phase:'Verify', schema:REVIEW_SCHEMA})))
const findings = reviews.filter(Boolean).flatMap(r=>r.findings||[])
const blockers = findings.filter(f=>f.severity==='blocker'||f.severity==='major')

phase('Fix')
let fixResult = 'No blocker/major findings.'
if (blockers.length>0) {
  fixResult = await agent(`${CTX}\n\nFix EACH blocker/major defect by editing the offending file (Read first, minimal diff, no regressions, no git).\n\nDEFECTS:\n${JSON.stringify(blockers,null,2)}\n\nReturn what you changed per file.`, {label:'fix', phase:'Fix'})
}

return { design, integration, totalFindings: findings.length, blockers: blockers.length, findings, fixResult }
