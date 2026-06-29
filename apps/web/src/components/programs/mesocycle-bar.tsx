"use client";

import { motion } from "motion/react";

import { soft } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";
import type { ProgramPosition } from "@/lib/programs/types";

/**
 * The cycle bar (`.meso`): one cell per microcycle repetition in the mesocycle —
 * completed (filled accent), current (accent outline), future (empty) — plus a
 * trailing dashed deload cell when `auto_deload`. Labelled "Cycle N of M" off
 * `mesocycle_length_microcycles`. Continuous programs (mesocycle length of one
 * and no auto-deload) collapse to a single caption line.
 *
 * On mount each cell fills via a staggered `scaleX`/opacity entrance (one-shot,
 * no looping animation); the current cell is highlighted statically by its `now`
 * class. Under reduced motion the entrance is dropped (cells appear static).
 */
export function MesocycleBar({
  position,
  autoDeload,
}: {
  position: ProgramPosition;
  autoDeload: boolean;
}) {
  const { reduced } = useReducedMotionSafe();
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
        {cells.map((c, i) => {
          const isDeload = c === deloadCell;
          const isCurrent = c === current && !isDeload;
          const cls = isDeload ? "deload" : c < current ? "done" : isCurrent ? "now" : "";
          return (
            <motion.div
              key={c}
              className={`wk ${cls}`}
              style={{ transformOrigin: "left center" }}
              initial={reduced ? false : { scaleX: 0, opacity: 0 }}
              animate={reduced ? undefined : { scaleX: 1, opacity: 1 }}
              transition={{ ...soft, delay: i * 0.05 }}
              title={isDeload ? "Deload" : undefined}
              aria-label={isDeload ? "Deload" : `Cycle ${c}`}
            />
          );
        })}
      </div>
    </div>
  );
}
