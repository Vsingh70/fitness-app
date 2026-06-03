import type { components } from "@/lib/api/types";

type Muscle = components["schemas"]["Muscle"];
type CurrentWeekMusclePoint = components["schemas"]["CurrentWeekMusclePoint"];

/**
 * Display order for the 19 muscles. Mirrors the Muscle enum in the generated
 * spec (chest -> calves), grouped roughly head-to-toe so the grid reads like
 * the prototype's body map.
 */
const MUSCLE_ORDER: Muscle[] = [
  "chest",
  "front_delts",
  "side_delts",
  "rear_delts",
  "traps",
  "rhomboids",
  "lats",
  "lower_back",
  "biceps",
  "triceps",
  "forearms",
  "abs",
  "obliques",
  "glutes",
  "quads",
  "hamstrings",
  "adductors",
  "abductors",
  "calves",
];

/**
 * Per-muscle weekly working-set targets. Primary movers use the 8-set
 * undertrained floor from 05.02 as a baseline; isolation muscles use a lower
 * band. The API current-week summary doesn't ship a target yet, so this table
 * is the client-side stand-in until one lands.
 */
const SET_TARGETS: Record<Muscle, number> = {
  chest: 12,
  front_delts: 8,
  side_delts: 9,
  rear_delts: 9,
  traps: 8,
  rhomboids: 9,
  lats: 12,
  lower_back: 8,
  biceps: 10,
  triceps: 10,
  forearms: 6,
  abs: 8,
  obliques: 6,
  glutes: 10,
  quads: 12,
  hamstrings: 10,
  adductors: 6,
  abductors: 6,
  calves: 9,
};

/** Maps a sets/target ratio to one of the five --heat-N ramp levels. */
function heatLevel(sets: number, target: number): 0 | 1 | 2 | 3 | 4 {
  if (!sets || !target) return 0;
  const r = sets / target;
  if (r >= 1.2) return 4;
  if (r >= 0.9) return 3;
  if (r >= 0.6) return 2;
  if (r > 0) return 1;
  return 0;
}

function muscleLabel(m: Muscle): string {
  return m.replace(/_/g, " ");
}

interface MuscleHeatmapProps {
  perMuscle: CurrentWeekMusclePoint[];
}

export function MuscleHeatmap({ perMuscle }: MuscleHeatmapProps) {
  const byMuscle = new Map<Muscle, number>();
  for (const p of perMuscle) {
    byMuscle.set(p.muscle, Math.round(Number(p.working_sets)));
  }

  return (
    <div>
      <div className="grid grid-cols-3 gap-2 p-4 sm:grid-cols-4">
        {MUSCLE_ORDER.map((m) => {
          const sets = byMuscle.get(m) ?? 0;
          const target = SET_TARGETS[m];
          const level = heatLevel(sets, target);
          const filled = level >= 1;
          return (
            <div
              key={m}
              title={`${muscleLabel(m)}: ${sets} of ${target} sets`}
              style={{
                background: `var(--heat-${level})`,
                color: level === 4 ? "var(--color-accent-foreground)" : undefined,
              }}
              className={
                "relative flex flex-col gap-0.5 rounded-[10px] p-3 transition-transform hover:-translate-y-px " +
                (filled ? "border border-transparent" : "border-border bg-surface border")
              }
            >
              <span
                className={
                  "text-[11px] font-medium capitalize " +
                  (level === 4
                    ? "text-[color-mix(in_oklab,white_85%,transparent)]"
                    : "text-text-secondary")
                }
              >
                {muscleLabel(m)}
              </span>
              <span className="font-serif text-xl leading-tight font-medium tracking-tight tabular-nums">
                {sets}
              </span>
              <span
                className={
                  "text-[10px] " +
                  (level === 4
                    ? "text-[color-mix(in_oklab,white_75%,transparent)]"
                    : "text-text-tertiary")
                }
              >
                target {target}
              </span>
            </div>
          );
        })}
      </div>

      <div className="border-border flex items-center justify-between border-t px-4 py-3">
        <div className="text-text-tertiary flex items-center gap-2 text-[11px]">
          <span>Less</span>
          <span className="flex gap-[3px]">
            <span
              className="border-border h-3.5 w-3.5 rounded-[3px] border"
              style={{ background: "var(--heat-0)" }}
            />
            <span className="h-3.5 w-3.5 rounded-[3px]" style={{ background: "var(--heat-1)" }} />
            <span className="h-3.5 w-3.5 rounded-[3px]" style={{ background: "var(--heat-2)" }} />
            <span className="h-3.5 w-3.5 rounded-[3px]" style={{ background: "var(--heat-3)" }} />
            <span className="h-3.5 w-3.5 rounded-[3px]" style={{ background: "var(--heat-4)" }} />
          </span>
          <span>More</span>
        </div>
        <span className="text-text-tertiary text-[11px]">Working sets this week vs target.</span>
      </div>
    </div>
  );
}
