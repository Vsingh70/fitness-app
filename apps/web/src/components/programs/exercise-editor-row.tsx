"use client";

import { GripVertical, Trash2 } from "lucide-react";
import { AnimatePresence, type DragControls, motion } from "motion/react";
import { useEffect, useState } from "react";

import { MiniSegmented } from "@/components/programs/mini-segmented";
import { RestPicker } from "@/components/programs/rest-picker";
import { snappy } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";
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
 * labelled control row — Sets, a Range/Target rep toggle, the {RPE|RIR} target
 * (a single box, shown only when the program intensity mode isn't Off), and a
 * fixed-step Rest dropdown. Switching rep mode / intensity mode animates the
 * value boxes' width (collapse/expand); the segmented toggle's highlight slides.
 * When a `dragControls` is
 * supplied the grip starts a row drag (reorder). Numeric fields commit on
 * blur/Enter and revert on invalid input. Reduced-motion collapses to fades.
 */
export function ExerciseEditorRow({
  pde,
  name,
  muscle,
  intensityMode,
  dragControls,
  onUpdate,
  onDelete,
}: {
  pde: ProgramDayExercise;
  name: string;
  muscle?: string;
  intensityMode: IntensityMode;
  dragControls?: DragControls;
  onUpdate: (body: ProgramDayExerciseUpdate) => void;
  onDelete: () => void;
}) {
  const { reduced } = useReducedMotionSafe();
  const isRpe = intensityMode === "rpe";
  const intensityValue = toNumber(isRpe ? pde.target_rpe_low : pde.target_rir_low);

  const setRepMode = (mode: RepMode) => {
    if (mode === pde.rep_mode) return;
    const body: ProgramDayExerciseUpdate = { rep_mode: mode };
    // Collapsing to a single goal mirrors low→high; expanding to a range seeds the
    // high bound from the existing goal so the field shows a valid span.
    if (mode === "target") body.target_reps_high = pde.target_reps_low;
    else if (pde.target_reps_low !== null) body.target_reps_high = pde.target_reps_low;
    onUpdate(body);
  };

  // A single intensity box writes both bounds (low === high), mirroring Target reps.
  const commitIntensity = (n: number | null) =>
    onUpdate(
      isRpe ? { target_rpe_low: n, target_rpe_high: n } : { target_rir_low: n, target_rir_high: n },
    );

  return (
    <div className="ew-ex">
      <div className="ew-ex-top">
        <span
          className="gr"
          aria-hidden={dragControls ? undefined : true}
          role={dragControls ? "button" : undefined}
          aria-label={dragControls ? `Drag to reorder ${name}` : undefined}
          tabIndex={dragControls ? -1 : undefined}
          style={dragControls ? { cursor: "grab", touchAction: "none" } : undefined}
          onPointerDown={dragControls ? (e) => dragControls.start(e) : undefined}
        >
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
            {/* Primary rep box is always present (the goal in Target, the low
                bound in Range). The "– high" tail collapses/expands its width
                via AnimatePresence — the same mechanism as the intensity box
                below — so switching Range↔Target morphs smoothly. */}
            <span className="ew-repval">
              <EwField
                ariaLabel={pde.rep_mode === "target" ? "Rep goal" : "Reps low"}
                value={pde.target_reps_low}
                min={1}
                max={100}
                allowEmpty
                onCommit={(n) => {
                  if (pde.rep_mode === "target") {
                    onUpdate({ target_reps_low: n, target_reps_high: n });
                    return;
                  }
                  const body: ProgramDayExerciseUpdate = { target_reps_low: n };
                  if (n === null) body.target_reps_high = null;
                  else if (pde.target_reps_high !== null && pde.target_reps_high < n)
                    body.target_reps_high = n;
                  onUpdate(body);
                }}
              />
              <AnimatePresence initial={false}>
                {pde.rep_mode === "range" ? (
                  <motion.span
                    key="reps-high"
                    className="ew-rangetail"
                    initial={reduced ? { opacity: 0 } : { width: 0, opacity: 0 }}
                    animate={reduced ? { opacity: 1 } : { width: "auto", opacity: 1 }}
                    exit={reduced ? { opacity: 0 } : { width: 0, opacity: 0 }}
                    transition={snappy}
                  >
                    <span className="dash">–</span>
                    <EwField
                      ariaLabel="Reps high"
                      value={pde.target_reps_high}
                      min={1}
                      max={100}
                      allowEmpty
                      onCommit={(n) => {
                        const body: ProgramDayExerciseUpdate = { target_reps_high: n };
                        if (n !== null) {
                          if (pde.target_reps_low === null) body.target_reps_low = n;
                          else if (n < pde.target_reps_low)
                            body.target_reps_high = pde.target_reps_low;
                        }
                        onUpdate(body);
                      }}
                    />
                  </motion.span>
                ) : null}
              </AnimatePresence>
            </span>
          </div>
        </div>

        <AnimatePresence initial={false}>
          {intensityMode !== "off" ? (
            <motion.div
              key="intensity"
              className="ew-cg"
              initial={reduced ? { opacity: 0 } : { width: 0, opacity: 0 }}
              animate={reduced ? { opacity: 1 } : { width: "auto", opacity: 1 }}
              exit={reduced ? { opacity: 0 } : { width: 0, opacity: 0 }}
              transition={snappy}
              style={{ overflow: "hidden" }}
            >
              <span className="lab">{isRpe ? "RPE" : "RIR"} target</span>
              <div className="body">
                <EwField
                  ariaLabel={`${isRpe ? "RPE" : "RIR"} target`}
                  value={intensityValue}
                  min={0}
                  max={10}
                  allowEmpty
                  allowHalf={isRpe}
                  onCommit={commitIntensity}
                />
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>

        <div className="ew-cg">
          <span className="lab">Rest</span>
          <div className="body">
            <RestPicker value={pde.rest_seconds} onChange={(s) => onUpdate({ rest_seconds: s })} />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Compact `.ew-field` numeric input; commits on blur/Enter, reverts on invalid.
 * With `allowHalf` it accepts 0.5 steps (RPE); otherwise integers only.
 */
function EwField({
  value,
  min,
  max,
  allowEmpty = false,
  allowHalf = false,
  ariaLabel,
  onCommit,
}: {
  value: number | null;
  min: number;
  max: number;
  allowEmpty?: boolean;
  allowHalf?: boolean;
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
    const wellFormed = allowHalf
      ? Number.isFinite(n) && Number.isInteger(n * 2)
      : Number.isInteger(n);
    if (!wellFormed || n < min || n > max) {
      setDraft(value === null ? "" : String(value));
      return;
    }
    if (n !== value) onCommit(n);
  };

  return (
    <input
      aria-label={ariaLabel}
      type="number"
      inputMode={allowHalf ? "decimal" : "numeric"}
      min={min}
      max={max}
      step={allowHalf ? 0.5 : 1}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
      }}
      className="ew-field"
    />
  );
}
