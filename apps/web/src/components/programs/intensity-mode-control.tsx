"use client";

import { MiniSegmented } from "@/components/programs/mini-segmented";
import type { IntensityMode } from "@/lib/programs/types";

const INTENSITY_OPTIONS: readonly { value: IntensityMode; label: string }[] = [
  { value: "rpe", label: "RPE" },
  { value: "rir", label: "RIR" },
  { value: "off", label: "Off" },
];

/**
 * The program-wide intensity-tracking control: a single RPE / RIR / Off choice
 * that governs every exercise. When Off, per-exercise rows hide their intensity
 * target entirely. Lives in the builder's Details panel.
 */
export function IntensityModeControl({
  value,
  onChange,
  disabled,
}: {
  value: IntensityMode;
  onChange: (mode: IntensityMode) => void;
  disabled?: boolean;
}) {
  return (
    <div>
      <div className="pw-kicker" style={{ marginBottom: 8 }}>
        Intensity tracking
      </div>
      <MiniSegmented
        options={INTENSITY_OPTIONS}
        value={value}
        onChange={onChange}
        disabled={disabled}
        ariaLabel="Intensity tracking scale"
      />
      <p className="ew-hint">Applies to every exercise in the program.</p>
    </div>
  );
}
