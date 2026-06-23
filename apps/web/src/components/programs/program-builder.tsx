"use client";

import { GripVertical } from "lucide-react";
import { AnimatePresence, Reorder, motion, useDragControls } from "motion/react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ExerciseEditorRow } from "@/components/programs/exercise-editor-row";
import { IntensityModeControl } from "@/components/programs/intensity-mode-control";
import { MiniSegmented } from "@/components/programs/mini-segmented";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/components/ui/toast";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import {
  useActivateProgram,
  useAddExerciseToSlot,
  useAddSlot,
  useDeactivateProgram,
  useDeleteProgramExercise,
  useDeleteSlot,
  useProgram,
  useReorderSlots,
  useToggleRest,
  useUpdateProgram,
  useUpdateProgramExercise,
} from "@/lib/hooks/programs";
import { snappy, soft } from "@/lib/motion/springs";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";
import { computeVolume } from "@/lib/programs/volume";
import type {
  IntensityMode,
  PeriodizationMode,
  ProgramDay,
  ProgramDayExerciseUpdate,
} from "@/lib/programs/types";

const PERIODIZATION_OPTIONS: readonly { value: PeriodizationMode; label: string }[] = [
  { value: "block", label: "Block" },
  { value: "continuous", label: "Cont." },
];

const ExercisePicker = dynamic(
  () => import("@/components/workouts/exercise-picker").then((m) => m.ExercisePicker),
  { ssr: false },
);

/**
 * Program builder (`.ew-grid`): a draggable slot rail + Details panel on the
 * left and the selected slot's exercise list on the right. The microcycle length
 * is simply the slot count (shown live); there is no forced day-per-week gate.
 * Reps are per-exercise (Range vs Target); intensity is one program-wide
 * RPE/RIR/Off setting. When periodization is on, the Details panel exposes the
 * mesocycle length (microcycles, deload excluded) and an auto-deload toggle —
 * editable on any program, including template-derived copies. Every edit is
 * persisted immediately through the program hooks. Motion: slots reorder with
 * `Reorder` + `layout` springs, a new slot springs in, and the rest-toggle
 * cross-fades the exercise panel — all collapsed under `prefers-reduced-motion`.
 */
export function ProgramBuilder({ programId }: { programId: string }) {
  const program = useProgram(programId);
  const updateProgram = useUpdateProgram(programId);
  const addSlot = useAddSlot(programId);
  const deleteSlot = useDeleteSlot(programId);
  const reorderSlots = useReorderSlots(programId);
  const toggleRest = useToggleRest(programId);
  const addExercise = useAddExerciseToSlot(programId);
  const updateExercise = useUpdateProgramExercise(programId);
  const deleteExercise = useDeleteProgramExercise(programId);
  const activate = useActivateProgram(programId);
  const deactivate = useDeactivateProgram(programId);
  const pushToast = useToastStore((s) => s.push);
  const { reduced } = useReducedMotionSafe();

  const [currentSlotId, setCurrentSlotId] = useState<string | null>(null);
  const [pickerOpenForSlot, setPickerOpenForSlot] = useState<string | null>(null);
  // Local mirror of the slot order so a drag reorders instantly; the persisted
  // server order re-syncs it on the program's next render.
  const [order, setOrder] = useState<ProgramDay[]>([]);

  const serverSlots = useMemo(
    () => (program.data ? [...program.data.days].sort((a, b) => a.slot_index - b.slot_index) : []),
    [program.data],
  );

  // Keep the local order in step with the server whenever its slot set changes
  // (add/delete/persisted reorder) — keyed on the id sequence, not identity.
  const serverKey = serverSlots.map((s) => s.id).join("|");
  useEffect(() => {
    setOrder(serverSlots);
  }, [serverKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const exerciseIds = useMemo(
    () =>
      program.data ? program.data.days.flatMap((d) => d.exercises.map((e) => e.exercise_id)) : [],
    [program.data],
  );
  const exMeta = useExerciseMeta(exerciseIds);
  const metaMap = exMeta.data ?? new Map();

  if (program.isLoading) return <p className="text-text-secondary">Loading program…</p>;
  if (program.isError || !program.data)
    return <p className="text-destructive">Could not load program.</p>;

  const p = program.data;
  const slots = order.length > 0 ? order : serverSlots;
  const activeSlot =
    slots.find((s) => s.id === currentSlotId) ?? slots[0] ?? null;
  const slotCount = slots.length;
  const isContinuous = p.periodization_mode === "continuous";
  const trainingSlots = slots.filter((d) => !d.is_rest_day).length;
  const volume = computeVolume(p, metaMap);

  const setMode = (mode: PeriodizationMode) => {
    if (mode !== p.periodization_mode) updateProgram.mutate({ periodization_mode: mode });
  };
  const setIntensityMode = (mode: IntensityMode) => {
    if (mode !== p.intensity_mode) updateProgram.mutate({ intensity_mode: mode });
  };
  const onUpdateExercise = (pdeId: string, body: ProgramDayExerciseUpdate) =>
    updateExercise.mutate(
      { pdeId, body },
      {
        onError: () => pushToast({ kind: "error", message: "Could not update exercise targets." }),
      },
    );

  const persistOrder = (next: ProgramDay[]) => {
    const before = next.map((s) => s.id);
    if (before.join("|") === serverSlots.map((s) => s.id).join("|")) return;
    reorderSlots.mutate(next.map((s) => s.id));
  };

  const onAddSlot = () => {
    addSlot.mutate(
      { name: `Slot ${slotCount + 1}`, is_rest_day: false },
      { onSuccess: (slot) => setCurrentSlotId(slot.id) },
    );
  };

  return (
    <div className="page-shell flex flex-col gap-5">
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-text-tertiary text-xs">
            <Link href={`/programs/${p.id}`} className="hover:text-text">
              {p.name}
            </Link>{" "}
            › Edit
          </p>
          <h1 className="font-serif text-[length:var(--text-h2)] leading-tight font-medium tracking-tight">
            {p.name}
          </h1>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Link href={`/programs/${p.id}`}>
            <Button type="button" variant="secondary" size="sm">
              Done
            </Button>
          </Link>
          {p.is_active ? (
            <Button
              type="button"
              size="sm"
              onClick={() => deactivate.mutate()}
              disabled={deactivate.isPending}
            >
              Deactivate
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              onClick={() =>
                activate.mutate(undefined, {
                  onError: (e) =>
                    pushToast({
                      kind: "error",
                      message:
                        (e as unknown as { message?: string })?.message ??
                        "Could not activate program.",
                    }),
                })
              }
              disabled={activate.isPending || trainingSlots < 1}
            >
              {activate.isPending ? "Activating…" : "Save & activate"}
            </Button>
          )}
        </div>
      </header>

      <div className="ew-grid">
        {/* Left rail: draggable slots + details + periodization + intensity + volume */}
        <aside>
          <div className="pw-kicker" style={{ marginBottom: 10 }}>
            {slotCount}-slot microcycle
          </div>
          <Reorder.Group
            axis="y"
            values={slots}
            onReorder={setOrder}
            className="ew-days"
            as="div"
          >
            <AnimatePresence initial={false}>
              {slots.map((slot) => (
                <SlotRailItem
                  key={slot.id}
                  slot={slot}
                  active={slot.id === activeSlot?.id}
                  reduced={reduced}
                  onSelect={() => setCurrentSlotId(slot.id)}
                  onToggleRest={(isRest) =>
                    toggleRest.mutate({ slotId: slot.id, isRestDay: isRest })
                  }
                  onDragEnd={() => persistOrder(slots)}
                />
              ))}
            </AnimatePresence>
          </Reorder.Group>
          <button type="button" className="ew-dtab add" onClick={onAddSlot}>
            + Add slot
          </button>

          <div className="pw-kicker" style={{ marginTop: 20 }}>
            Details
          </div>
          <div className="ew-details">
            <div>
              Goal — <b className="capitalize">{p.goal.replace(/_/g, " ")}</b>
            </div>
            <div>
              Progression — <b>{isContinuous ? "Continuous" : "Periodized block"}</b>
            </div>
            <div>
              Microcycle — <b>{slotCount} slots</b>
            </div>
            <div>
              Status — <b>{p.is_active ? "Active" : "Draft"}</b>
            </div>
          </div>

          <div className="pw-kicker" style={{ marginTop: 18 }}>
            Periodization
          </div>
          <div style={{ marginTop: 8 }}>
            <MiniSegmented
              options={PERIODIZATION_OPTIONS}
              value={p.periodization_mode}
              onChange={setMode}
              disabled={updateProgram.isPending}
              ariaLabel="Periodization mode"
            />
            {isContinuous ? (
              <label className="ew-check">
                <input
                  type="checkbox"
                  checked={p.auto_deload_on_stall}
                  onChange={(e) => updateProgram.mutate({ auto_deload_on_stall: e.target.checked })}
                />
                Suggest a deload when a lift stalls
              </label>
            ) : (
              <div className="ew-meso">
                <span className="lab">Mesocycle length</span>
                <div className="ew-meso-row">
                  <MesoField
                    value={p.mesocycle_length_microcycles}
                    onCommit={(n) => {
                      if (n !== p.mesocycle_length_microcycles)
                        updateProgram.mutate({ mesocycle_length_microcycles: n });
                    }}
                  />
                  <span className="unit">microcycles</span>
                </div>
                <p className="ew-hint">Repetitions before a deload; the deload isn’t counted.</p>
                <label className="ew-check" style={{ marginTop: 10 }}>
                  <input
                    type="checkbox"
                    checked={p.auto_deload}
                    onChange={(e) => updateProgram.mutate({ auto_deload: e.target.checked })}
                  />
                  Auto-deload after each mesocycle
                </label>
              </div>
            )}
          </div>

          <div style={{ marginTop: 18 }}>
            <IntensityModeControl
              value={p.intensity_mode}
              onChange={setIntensityMode}
              disabled={updateProgram.isPending}
            />
          </div>

          {volume.length > 0 ? (
            <>
              <div className="pw-kicker" style={{ marginTop: 18 }}>
                Weekly volume
              </div>
              <div style={{ marginTop: 8 }}>
                {volume.map((v) => (
                  <div className="ew-vol-row" key={v.muscle}>
                    <span className="mu">{v.muscle.replace(/_/g, " ")}</span>
                    <span className={`ct ${v.status === "ok" ? "" : "warn"}`}>{v.sets}</span>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </aside>

        {/* Right: selected slot's exercises (or its rest state), cross-faded */}
        <section className="ew-canvas">
          {activeSlot ? (
            <>
              <div className="h">
                <span className="t">{activeSlot.name}</span>
                <div className="flex items-center gap-3">
                  <label className="ew-check" style={{ margin: 0 }}>
                    <input
                      type="checkbox"
                      checked={activeSlot.is_rest_day}
                      onChange={(e) =>
                        toggleRest.mutate({ slotId: activeSlot.id, isRestDay: e.target.checked })
                      }
                    />
                    Rest day
                  </label>
                  <button
                    type="button"
                    className="pw-link"
                    onClick={() => {
                      deleteSlot.mutate(activeSlot.id);
                      setCurrentSlotId(null);
                    }}
                    style={{ color: "var(--color-text-tertiary)" }}
                  >
                    Delete slot
                  </button>
                </div>
              </div>

              <AnimatePresence mode="wait" initial={false}>
                {activeSlot.is_rest_day ? (
                  <motion.p
                    key="rest"
                    className="text-text-secondary py-4 text-sm"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={snappy}
                  >
                    Rest day, no exercises.
                  </motion.p>
                ) : (
                  <motion.div
                    key="exercises"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={snappy}
                  >
                    {activeSlot.exercises.length === 0 ? (
                      <p className="text-text-secondary py-4 text-sm">No exercises yet.</p>
                    ) : (
                      activeSlot.exercises.map((pde) => (
                        <ExerciseEditorRow
                          key={pde.id}
                          pde={pde}
                          name={metaMap.get(pde.exercise_id)?.name ?? "Exercise"}
                          muscle={metaMap.get(pde.exercise_id)?.primary_muscle ?? undefined}
                          intensityMode={p.intensity_mode}
                          onUpdate={(body) => onUpdateExercise(pde.id, body)}
                          onDelete={() => deleteExercise.mutate(pde.id)}
                        />
                      ))
                    )}

                    <button
                      type="button"
                      className="ew-add"
                      onClick={() => setPickerOpenForSlot(activeSlot.id)}
                    >
                      + Add exercise to {activeSlot.name}
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          ) : (
            <p className="text-text-secondary text-sm">Add a slot to start building.</p>
          )}
        </section>
      </div>

      <ExercisePicker
        open={pickerOpenForSlot !== null}
        onOpenChange={(o) => {
          if (!o) setPickerOpenForSlot(null);
        }}
        onPick={(ex) => {
          if (pickerOpenForSlot) {
            addExercise.mutate({
              slotId: pickerOpenForSlot,
              body: {
                exercise_id: ex.id,
                target_sets: 3,
                progression_strategy: "none",
                rep_mode: "range",
              },
            });
            setPickerOpenForSlot(null);
          }
        }}
      />
    </div>
  );
}

/**
 * One draggable slot row in the rail. Drag is initiated only from the grip
 * handle (`dragListener={false}` + `useDragControls`) so the name button and
 * rest checkbox stay clickable. Springs in via `AnimatePresence`; layout
 * animation is dropped under reduced motion.
 */
function SlotRailItem({
  slot,
  active,
  reduced,
  onSelect,
  onToggleRest,
  onDragEnd,
}: {
  slot: ProgramDay;
  active: boolean;
  reduced: boolean;
  onSelect: () => void;
  onToggleRest: (isRest: boolean) => void;
  onDragEnd: () => void;
}) {
  const controls = useDragControls();
  return (
    <Reorder.Item
      value={slot}
      dragListener={false}
      dragControls={controls}
      layout={reduced ? undefined : "position"}
      initial={reduced ? { opacity: 0 } : { opacity: 0, y: -6 }}
      animate={reduced ? { opacity: 1 } : { opacity: 1, y: 0 }}
      exit={reduced ? { opacity: 0 } : { opacity: 0, y: -6 }}
      transition={soft}
      onDragEnd={onDragEnd}
      className={`ew-dtab ${active ? "on" : ""}`}
      as="div"
    >
      <span
        className="gr"
        aria-label="Drag to reorder slot"
        role="button"
        tabIndex={-1}
        style={{ cursor: "grab", touchAction: "none" }}
        onPointerDown={(e) => controls.start(e)}
      >
        <GripVertical size={14} />
      </span>
      <button
        type="button"
        className="nm"
        onClick={onSelect}
        style={{ background: "none", border: 0, padding: 0, textAlign: "left", flex: 1 }}
      >
        {slot.name}
      </button>
      <label className="ew-slot-rest" title={slot.is_rest_day ? "Rest slot" : "Training slot"}>
        <input
          type="checkbox"
          checked={slot.is_rest_day}
          onChange={(e) => onToggleRest(e.target.checked)}
        />
        <span>Rest</span>
      </label>
    </Reorder.Item>
  );
}

/** Compact numeric stepper for the mesocycle length (1–12 microcycles). */
function MesoField({
  value,
  onCommit,
}: {
  value: number;
  onCommit: (value: number) => void;
}) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  const commit = () => {
    const n = Number(draft.trim());
    if (!Number.isInteger(n) || n < 1 || n > 12) {
      setDraft(String(value));
      return;
    }
    if (n !== value) onCommit(n);
  };

  return (
    <input
      aria-label="Mesocycle length in microcycles"
      type="number"
      inputMode="numeric"
      min={1}
      max={12}
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
