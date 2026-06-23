"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import type {
  IntensityMode,
  ProgramDayExercise,
  ProgramDayExerciseUpdate,
} from "@/lib/programs/types";

/** Parse a stored RPE/RIR column (the API serialises RPE as a numeric string). */
function toNumber(value: number | string | null): number | null {
  if (value == null) return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

/**
 * Compact targets editor for the in-session "Change in program" path (05 §3).
 * Edits sets, the rep range, and the intensity target on a slot exercise, then
 * commits the whole diff in one PATCH. It reuses the builder's field semantics
 * (numeric commit, revert on invalid) but stays inside the action sheet so the
 * change is one-handed and never nests a third modal.
 */
export function ProgramTargetEditor({
  pde,
  intensityMode,
  saving = false,
  onSave,
  onCancel,
}: {
  pde: ProgramDayExercise;
  intensityMode: IntensityMode;
  saving?: boolean;
  onSave: (body: ProgramDayExerciseUpdate) => void;
  onCancel: () => void;
}) {
  const isRpe = intensityMode === "rpe";
  const [sets, setSets] = useState(String(pde.target_sets));
  const [repsLow, setRepsLow] = useState(
    pde.target_reps_low === null ? "" : String(pde.target_reps_low),
  );
  const [repsHigh, setRepsHigh] = useState(
    pde.target_reps_high === null ? "" : String(pde.target_reps_high),
  );
  const initialIntLow = toNumber(isRpe ? pde.target_rpe_low : pde.target_rir_low);
  const initialIntHigh = toNumber(isRpe ? pde.target_rpe_high : pde.target_rir_high);
  const [intLow, setIntLow] = useState(initialIntLow === null ? "" : String(initialIntLow));
  const [intHigh, setIntHigh] = useState(initialIntHigh === null ? "" : String(initialIntHigh));

  const num = (raw: string): number | null => {
    const t = raw.trim();
    if (t === "") return null;
    const n = Number(t);
    return Number.isFinite(n) ? n : null;
  };

  const submit = () => {
    const body: ProgramDayExerciseUpdate = {};
    const s = num(sets);
    if (s !== null && s !== pde.target_sets) body.target_sets = s;
    const rl = num(repsLow);
    const rh = num(repsHigh);
    if (rl !== pde.target_reps_low) body.target_reps_low = rl;
    if (rh !== pde.target_reps_high) body.target_reps_high = rh;
    const il = num(intLow);
    const ih = num(intHigh);
    if (isRpe) {
      if (il !== initialIntLow) body.target_rpe_low = il;
      if (ih !== initialIntHigh) body.target_rpe_high = ih;
    } else {
      if (il !== initialIntLow) body.target_rir_low = il;
      if (ih !== initialIntHigh) body.target_rir_high = ih;
    }
    onSave(body);
  };

  return (
    <div className="flex flex-col gap-4">
      <Field label="Sets">
        <NumInput aria-label="Target sets" value={sets} onChange={setSets} />
      </Field>
      <Field label="Reps">
        <div className="flex items-center gap-2">
          <NumInput aria-label="Reps low" value={repsLow} onChange={setRepsLow} />
          <span className="text-text-tertiary">–</span>
          <NumInput aria-label="Reps high" value={repsHigh} onChange={setRepsHigh} />
        </div>
      </Field>
      {intensityMode !== "off" ? (
        <Field label={`${isRpe ? "RPE" : "RIR"} target`}>
          <div className="flex items-center gap-2">
            <NumInput
              aria-label={`${isRpe ? "RPE" : "RIR"} low`}
              value={intLow}
              onChange={setIntLow}
            />
            <span className="text-text-tertiary">–</span>
            <NumInput
              aria-label={`${isRpe ? "RPE" : "RIR"} high`}
              value={intHigh}
              onChange={setIntHigh}
            />
          </div>
        </Field>
      ) : null}
      <p className="text-text-tertiary text-xs">
        Applies to this program now and every future cycle. Sets you already logged this session
        stay as they are.
      </p>
      <div className="flex items-center justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button type="button" size="sm" onClick={submit} disabled={saving}>
          {saving ? "Saving…" : "Save to program"}
        </Button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex items-center justify-between gap-4">
      <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.1em] uppercase">
        {label}
      </span>
      {children}
    </label>
  );
}

function NumInput({
  value,
  onChange,
  ...rest
}: {
  value: string;
  onChange: (v: string) => void;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange">) {
  return (
    <input
      type="number"
      inputMode="numeric"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="bg-surface border-border text-text h-9 w-[5.5rem] rounded-[var(--radius-button)] border px-2 text-right font-serif font-medium tabular-nums"
      {...rest}
    />
  );
}
