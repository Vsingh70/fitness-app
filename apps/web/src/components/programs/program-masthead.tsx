"use client";

import { MesocycleBar } from "@/components/programs/mesocycle-bar";
import type { Program, ProgramPosition } from "@/lib/programs/types";

/**
 * The active-program masthead (`.aw-mast`): kicker + serif program name, a
 * right-aligned Goal / Strategy / Microcycle meta row, and the mesocycle bar
 * underneath. Used by the overview (`/programs`) and the per-program view.
 */
export function ProgramMasthead({
  program,
  position,
  kicker = "Active program",
  hideCycleBar = false,
}: {
  program: Program;
  position?: ProgramPosition;
  kicker?: string;
  /** Suppress the embedded cycle bar so the spine can reveal it as its own step. */
  hideCycleBar?: boolean;
}) {
  const strategy = program.periodization_mode === "continuous" ? "Continuous" : "Periodized";
  const trainingSlots = program.days.filter((d) => !d.is_rest_day).length;
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
            <div className="v">
              {program.microcycle_length}-slot cycle, {trainingSlots} training
            </div>
            <div className="l">Microcycle</div>
          </div>
        </div>
      </div>
      {position && !hideCycleBar ? (
        <MesocycleBar position={position} autoDeload={program.auto_deload} />
      ) : null}
    </div>
  );
}
