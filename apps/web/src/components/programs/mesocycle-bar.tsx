"use client";

import type { MesocyclePosition } from "@/lib/programs/types";

/**
 * The mesocycle progress bar (`.meso`): one cell per week — completed (filled
 * accent), current (accent outline), future (empty), deload (dashed). Mirrors the
 * design's `.aw-meso-wrap`. Continuous programs have no scheduled deload, so the
 * bar collapses to a single caption line.
 */
export function MesocycleBar({ meso }: { meso: MesocyclePosition }) {
  if (meso.is_continuous) {
    return (
      <div className="aw-meso-wrap">
        <div className="lab">
          <span>Continuous — no scheduled deload</span>
        </div>
      </div>
    );
  }

  const length = Math.max(1, meso.mesocycle_length_weeks);
  const current = meso.week_in_meso ?? 1;
  const deloadWeek = meso.auto_deload ? length : null;
  const weeks = Array.from({ length }, (_, i) => i + 1);

  return (
    <div className="aw-meso-wrap">
      <div className="lab">
        <span>
          Mesocycle · Week {current} of {length}
        </span>
        {deloadWeek ? <span>Week {deloadWeek} deload</span> : null}
      </div>
      <div className="meso">
        {weeks.map((w) => {
          const cls =
            w === deloadWeek ? "deload" : w < current ? "done" : w === current ? "now" : "";
          return (
            <div
              key={w}
              className={`wk ${cls}`}
              title={w === deloadWeek ? "Deload" : undefined}
              aria-label={`Week ${w}${w === deloadWeek ? " (deload)" : ""}`}
            />
          );
        })}
      </div>
    </div>
  );
}
