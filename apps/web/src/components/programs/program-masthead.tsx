"use client";

import { MesocycleBar } from "@/components/programs/mesocycle-bar";
import type { MesocyclePosition, Program } from "@/lib/programs/types";

/**
 * The active-program masthead (`.aw-mast`): kicker + serif program name, a
 * right-aligned Goal / Strategy / Frequency meta row, and the mesocycle bar
 * underneath. Used by the overview (`/programs`) and the per-program view.
 */
export function ProgramMasthead({
  program,
  meso,
  kicker = "Active program",
}: {
  program: Program;
  meso?: MesocyclePosition;
  kicker?: string;
}) {
  const strategy = program.periodization_mode === "continuous" ? "Continuous" : "Periodized";
  return (
    <div className="aw-mast">
      <div className="row">
        <div>
          <div className="pw-kicker">{kicker}</div>
          <div className="ti">{program.name}</div>
        </div>
        <div className="meta">
          <div className="m">
            <div className="v capitalize">{program.goal.replace(/_/g, " ")}</div>
            <div className="l">Goal</div>
          </div>
          <div className="m">
            <div className="v">{strategy}</div>
            <div className="l">Strategy</div>
          </div>
          <div className="m">
            <div className="v">{program.days_per_week}×/wk</div>
            <div className="l">Frequency</div>
          </div>
        </div>
      </div>
      {meso ? <MesocycleBar meso={meso} /> : null}
    </div>
  );
}
