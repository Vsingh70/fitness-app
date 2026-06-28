"use client";

import { GripVertical, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { MiniSegmented } from "@/components/programs/mini-segmented";
import type {
  IntensityMode,
  ProgramDayExercise,
  ProgramDayExerciseUpdate,
  RepMode,
} from "@/lib/programs/types";

const REP_MODE_OPTIONS: readonly { value: RepMode; label: string }[] = [
  { value: "range", label: "Range" },
  { value: "target", label: "Target" },
];

/** Parse a stored RPE/RIR column (the API serialises RPE as a numeric string). */
function toNumber(value: number | string | null): number | null {
  if (value == null) return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

/**
 * One builder exercise block (`.ew-ex`): grip + name + muscle + delete, then a
 * labelled control row — Sets, a per-exercise Range/Target rep toggle with its
 * value field(s), and the {RPE|RIR} target (shown only when the program-level
 * intensity mode isn't Off). Numeric fields commit on blur/Enter; invalid input
 * reverts. The two new fields the data model added are `rep_mode` and the
 * intensity columns chosen by `intensityMode`.
 */
export function ExerciseEditorRow({
  pde,
  name,
  muscle,
  intensityMode,
  onUpdate,
  onDelete,
}: {
  pde: ProgramDayExercise;
  name: string;
  muscle?: string;
  intensityMode: IntensityMode;
  onUpdate: (body: ProgramDayExerciseUpdate) => void;
  onDelete: () => void;
}) {
  const isRpe = intensityMode === "rpe";
  const intensityLow = toNumber(isRpe ? pde.target_rpe_low : pde.target_rir_low);
  const intensityHigh = toNumber(isRpe ? pde.target_rpe_high : pde.target_rir_high);

  const setRepMode = (mode: RepMode) => {
    if (mode === pde.rep_mode) return;
    const body: ProgramDayExerciseUpdate = { rep_mode: mode };
    // Collapsing to a single goal mirrors low→high; expanding to a range seeds the
    // high bound from the existing goal so the field shows a valid span.
    if (mode === "target") body.target_reps_high = pde.target_reps_low;
    else if (pde.target_reps_low !== null) body.target_reps_high = pde.target_reps_low;
    onUpdate(body);
  };

  const commitIntensity = (which: "low" | "high", n: number | null) => {
    const body: ProgramDayExerciseUpdate = {};
    if (isRpe) {
      if (which === "low") body.target_rpe_low = n;
      else body.target_rpe_high = n;
    } else if (which === "low") body.target_rir_low = n;
    else body.target_rir_high = n;
    onUpdate(body);
  };

  return (
    <div className="ew-ex">
      <div className="ew-ex-top">
        <span className="gr" aria-hidden>
          <GripVertical size={14} />
        </span>
        <span className="nm">{name}</span>
        {muscle ? <span className="mus">· {muscle.replace(/_/g, " ")}</span> : null}
        <button type="button" className="del" aria-label={`Remove ${name}`} onClick={onDelete}>
          <Trash2 size={15} />
        </button>
      </div>

      <div className="ew-ctl">
        <div className="ew-cg">
          <span className="lab">Sets</span>
          <div className="body">
            <EwField
              ariaLabel="Sets"
              value={pde.target_sets}
              min={1}
              max={20}
              onCommit={(n) => {
                if (n !== null) onUpdate({ target_sets: n });
              }}
            />
          </div>
        </div>

        <div className="ew-cg">
          <span className="lab">Reps</span>
          <div className="body">
            <MiniSegmented
              options={REP_MODE_OPTIONS}
              value={pde.rep_mode}
              onChange={setRepMode}
              ariaLabel="Rep mode"
            />
            {pde.rep_mode === "target" ? (
              <EwField
                ariaLabel="Rep goal"
                value={pde.target_reps_low}
                min={1}
                max={100}
                allowEmpty
                onCommit={(n) => onUpdate({ target_reps_low: n, target_reps_high: n })}
              />
            ) : (
              <span className="ew-rangepair">
                <EwField
                  sm
                  ariaLabel="Reps low"
                  value={pde.target_reps_low}
                  min={1}
                  max={100}
                  allowEmpty
                  onCommit={(n) => {
                    const body: ProgramDayExerciseUpdate = { target_reps_low: n };
                    if (n === null) body.target_reps_high = null;
                    else if (pde.target_reps_high !== null && pde.target_reps_high < n)
                      body.target_reps_high = n;
                    onUpdate(body);
                  }}
                />
                <span className="dash">–</span>
                <EwField
                  sm
                  ariaLabel="Reps high"
                  value={pde.target_reps_high}
                  min={1}
                  max={100}
                  allowEmpty
                  onCommit={(n) => {
                    const body: ProgramDayExerciseUpdate = { target_reps_high: n };
                    if (n !== null) {
                      if (pde.target_reps_low === null) body.target_reps_low = n;
                      else if (n < pde.target_reps_low) body.target_reps_high = pde.target_reps_low;
                    }
                    onUpdate(body);
                  }}
                />
              </span>
            )}
          </div>
        </div>

        {intensityMode !== "off" ? (
          <div className="ew-cg">
            <span className="lab">{isRpe ? "RPE" : "RIR"} target</span>
            <div className="body">
              <span className="ew-rangepair">
                <EwField
                  sm
                  ariaLabel={`${isRpe ? "RPE" : "RIR"} low`}
                  value={intensityLow}
                  min={0}
                  max={10}
                  allowEmpty
                  onCommit={(n) => commitIntensity("low", n)}
                />
                <span className="dash">–</span>
                <EwField
                  sm
                  ariaLabel={`${isRpe ? "RPE" : "RIR"} high`}
                  value={intensityHigh}
                  min={0}
                  max={10}
                  allowEmpty
                  onCommit={(n) => commitIntensity("high", n)}
                />
              </span>
            </div>
          </div>
        ) : null}

        <div className="ew-cg">
          <span className="lab">Rest</span>
          <div className="body">
            <EwField
              ariaLabel="Rest (seconds)"
              value={pde.rest_seconds}
              min={1}
              max={3600}
              allowEmpty
              onCommit={(n) => onUpdate({ rest_seconds: n })}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

/** Compact `.ew-field` numeric input; commits on blur/Enter, reverts on invalid. */
function EwField({
  value,
  min,
  max,
  allowEmpty = false,
  sm = false,
  ariaLabel,
  onCommit,
}: {
  value: number | null;
  min: number;
  max: number;
  allowEmpty?: boolean;
  sm?: boolean;
  ariaLabel: string;
  onCommit: (value: number | null) => void;
}) {
  const [draft, setDraft] = useState(value === null ? "" : String(value));
  useEffect(() => {
    setDraft(value === null ? "" : String(value));
  }, [value]);

  const commit = () => {
    const trimmed = draft.trim();
    if (trimmed === "") {
      if (!allowEmpty) {
        setDraft(value === null ? "" : String(value));
        return;
      }
      if (value !== null) onCommit(null);
      return;
    }
    const n = Number(trimmed);
    if (!Number.isInteger(n) || n < min || n > max) {
      setDraft(value === null ? "" : String(value));
      return;
    }
    if (n !== value) onCommit(n);
  };

  return (
    <input
      aria-label={ariaLabel}
      type="number"
      inputMode="numeric"
      min={min}
      max={max}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
      }}
      className={`ew-field${sm ? "sm" : ""}`}
    />
  );
}
