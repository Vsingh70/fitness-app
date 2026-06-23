"use client";

import type { ProgramPosition } from "@/lib/programs/types";

/**
 * The mesocycle progress bar (`.meso`): one cell per microcycle repetition —
 * completed (filled accent), current (accent outline), future (empty), deload
 * (dashed). Mirrors the design's `.aw-meso-wrap`. Continuous programs (mesocycle
 * length of one and no auto-deload) collapse to a single caption line.
 *
 * NOTE: this is the mechanical rebind to the flexible microcycle model; the full
 * cycle-bar redesign (per-repetition fill animation, "Cycle N of M" labelling)
 * lands in a later task.
 */
export function MesocycleBar({
  position,
  autoDeload,
}: {
  position: ProgramPosition;
  autoDeload: boolean;
}) {
  const length = Math.max(1, position.mesocycle_length_microcycles);

  if (length <= 1 && !autoDeload) {
    return (
      <div className="aw-meso-wrap">
        <div className="lab">
          <span>Continuous — no scheduled deload</span>
        </div>
      </div>
    );
  }

  const current = position.current_repetition;
  const deloadCell = autoDeload ? length + 1 : null;
  const cells = Array.from({ length: autoDeload ? length + 1 : length }, (_, i) => i + 1);

  return (
    <div className="aw-meso-wrap">
      <div className="lab">
        <span>
          Mesocycle · Cycle {current} of {length}
        </span>
        {deloadCell ? <span>Deload</span> : null}
      </div>
      <div className="meso">
        {cells.map((c) => {
          const cls =
            c === deloadCell ? "deload" : c < current ? "done" : c === current ? "now" : "";
          return (
            <div
              key={c}
              className={`wk ${cls}`}
              title={c === deloadCell ? "Deload" : undefined}
              aria-label={c === deloadCell ? "Deload" : `Cycle ${c}`}
            />
          );
        })}
      </div>
    </div>
  );
}
