"use client";

import { useQueryClient } from "@tanstack/react-query";
import { GripVertical, Trash2 } from "lucide-react";
import { AnimatePresence, Reorder, motion, useDragControls } from "motion/react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { ExerciseEditorRow } from "@/components/programs/exercise-editor-row";
import { IntensityModeControl } from "@/components/programs/intensity-mode-control";
import { MiniSegmented } from "@/components/programs/mini-segmented";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/components/ui/toast";
import type { ExerciseList } from "@/lib/api/exercises";
import { searchExercises } from "@/lib/api/workouts";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import { useMe } from "@/lib/hooks/me";
import {
  useActivateProgram,
  useAddExerciseToSlot,
  useAddSlot,
  useDeactivateProgram,
  useDeleteProgramExercise,
  useDeleteSlot,
  useProgram,
  useRenameSlot,
  useReorderExercises,
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
  ProgramDayExercise,
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
  const qc = useQueryClient();
  const program = useProgram(programId);
  const updateProgram = useUpdateProgram(programId);
  const addSlot = useAddSlot(programId);
  const deleteSlot = useDeleteSlot(programId);
  const reorderSlots = useReorderSlots(programId);
  const toggleRest = useToggleRest(programId);
  const renameSlot = useRenameSlot(programId);
  const addExercise = useAddExerciseToSlot(programId);
  const updateExercise = useUpdateProgramExercise(programId);
  const deleteExercise = useDeleteProgramExercise(programId);
  const reorderExercises = useReorderExercises(programId);
  const activate = useActivateProgram(programId);
  const deactivate = useDeactivateProgram(programId);
  const pushToast = useToastStore((s) => s.push);
  const me = useMe();
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

  // Keep the local drag mirror in step with the server on every program change
  // (rest/name/exercise edits, add/delete, persisted reorder) — not just when the
  // slot id-set changes. serverSlots is memoized on program.data, so this only
  // re-runs when the program actually changes, never mid-drag before persist.
  useEffect(() => {
    setOrder(serverSlots);
  }, [serverSlots]);

  // Warm the add-exercise flow so the first open is instant: preload the lazy
  // picker chunk and prefetch its default query (matches the picker's useQuery key).
  useEffect(() => {
    import("@/components/workouts/exercise-picker").catch(() => {});
    void qc.prefetchInfiniteQuery({
      queryKey: ["exercises", "all", ""],
      queryFn: ({ pageParam }) =>
        searchExercises(undefined, { mine_only: false, limit: 100, cursor: pageParam }),
      initialPageParam: undefined as string | undefined,
      getNextPageParam: (last: ExerciseList) => last.next_cursor ?? undefined,
      staleTime: 30_000,
    });
  }, [qc]);

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
  const activeSlot = slots.find((s) => s.id === currentSlotId) ?? slots[0] ?? null;
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
            <InlineNameField
              name={p.name}
              onRename={(name) => updateProgram.mutate({ name })}
              className="ew-prog-name"
              ariaLabel="Program name"
            />
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
          <Reorder.Group axis="y" values={slots} onReorder={setOrder} className="ew-days" as="div">
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
                  onDelete={() => {
                    deleteSlot.mutate(slot.id);
                    if (slot.id === currentSlotId) setCurrentSlotId(null);
                  }}
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
                <InlineNameField
                  key={activeSlot.id}
                  name={activeSlot.name}
                  onRename={(name) => renameSlot.mutate({ slotId: activeSlot.id, name })}
                />
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
                <motion.div
                  key={`${activeSlot.id}:${activeSlot.is_rest_day ? "rest" : "ex"}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={snappy}
                >
                  {activeSlot.is_rest_day ? (
                    <p className="text-text-secondary py-4 text-sm">Rest day, no exercises.</p>
                  ) : (
                    <>
                      <SlotExercises
                        slot={activeSlot}
                        intensityMode={p.intensity_mode}
                        reduced={reduced}
                        getName={(id) => metaMap.get(id)?.name ?? "Exercise"}
                        getMuscle={(id) => metaMap.get(id)?.primary_muscle ?? undefined}
                        onReorder={(slotId, orderedIds) =>
                          reorderExercises.mutate({ slotId, orderedIds })
                        }
                        onUpdateExercise={onUpdateExercise}
                        onDeleteExercise={(pdeId) => deleteExercise.mutate(pdeId)}
                        onAddExercise={() => setPickerOpenForSlot(activeSlot.id)}
                      />
                    </>
                  )}
                </motion.div>
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
                block_kind: "working",
                // Seed each new exercise with the user's default rest timer
                // (Settings → Default rest timer) rather than leaving it "None".
                rest_seconds: me.data?.default_rest_seconds ?? 90,
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
  onDelete,
  onDragEnd,
}: {
  slot: ProgramDay;
  active: boolean;
  reduced: boolean;
  onSelect: () => void;
  onToggleRest: (isRest: boolean) => void;
  onDelete: () => void;
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
      <button
        type="button"
        className="ew-slot-del"
        aria-label={`Delete ${slot.name}`}
        title="Delete slot"
        onClick={onDelete}
      >
        <Trash2 size={13} />
      </button>
    </Reorder.Item>
  );
}

/**
 * The active slot's exercises as a draggable list. Mirrors the slot rail: a
 * `Reorder.Group` over a local order mirror (synced from the slot, so a drag
 * isn't clobbered mid-flight); each row is drag-initiated from its grip. On drop
 * it persists the new order, and rows spring in/out on add/delete.
 */
function SlotExercises({
  slot,
  intensityMode,
  reduced,
  getName,
  getMuscle,
  onReorder,
  onUpdateExercise,
  onDeleteExercise,
  onAddExercise,
}: {
  slot: ProgramDay;
  intensityMode: IntensityMode;
  reduced: boolean;
  getName: (exerciseId: string) => string;
  getMuscle: (exerciseId: string) => string | undefined;
  onReorder: (slotId: string, orderedIds: string[]) => void;
  onUpdateExercise: (pdeId: string, body: ProgramDayExerciseUpdate) => void;
  onDeleteExercise: (pdeId: string) => void;
  onAddExercise: () => void;
}) {
  const [exOrder, setExOrder] = useState<ProgramDayExercise[]>(slot.exercises);
  // Re-sync from the server on every slot change (add/delete/persisted reorder);
  // stable during a drag since the program isn't mutated until drop.
  useEffect(() => {
    setExOrder(slot.exercises);
  }, [slot]);

  const persistOrder = () => {
    const before = slot.exercises.map((e) => e.id).join("|");
    const after = exOrder.map((e) => e.id).join("|");
    if (before !== after)
      onReorder(
        slot.id,
        exOrder.map((e) => e.id),
      );
  };

  return (
    <>
      <Reorder.Group axis="y" values={exOrder} onReorder={setExOrder} as="div">
        <AnimatePresence initial={false}>
          {exOrder.map((pde) => (
            <ExerciseReorderItem
              key={pde.id}
              pde={pde}
              name={getName(pde.exercise_id)}
              muscle={getMuscle(pde.exercise_id)}
              intensityMode={intensityMode}
              reduced={reduced}
              onUpdate={(body) => onUpdateExercise(pde.id, body)}
              onDelete={() => onDeleteExercise(pde.id)}
              onDragEnd={persistOrder}
            />
          ))}
        </AnimatePresence>
      </Reorder.Group>
      {exOrder.length === 0 ? (
        <p className="text-text-secondary py-4 text-sm">No exercises yet.</p>
      ) : null}
      <motion.button
        type="button"
        layout={!reduced}
        transition={soft}
        className="ew-add"
        onClick={onAddExercise}
      >
        + Add exercise to {slot.name}
      </motion.button>
    </>
  );
}

/** One draggable exercise row; drag starts from the row's grip handle. */
function ExerciseReorderItem({
  pde,
  name,
  muscle,
  intensityMode,
  reduced,
  onUpdate,
  onDelete,
  onDragEnd,
}: {
  pde: ProgramDayExercise;
  name: string;
  muscle?: string;
  intensityMode: IntensityMode;
  reduced: boolean;
  onUpdate: (body: ProgramDayExerciseUpdate) => void;
  onDelete: () => void;
  onDragEnd: () => void;
}) {
  const controls = useDragControls();
  return (
    <Reorder.Item
      value={pde}
      dragListener={false}
      dragControls={controls}
      layout={reduced ? undefined : "position"}
      initial={reduced ? { opacity: 0 } : { opacity: 0, y: -6 }}
      animate={reduced ? { opacity: 1 } : { opacity: 1, y: 0 }}
      exit={reduced ? { opacity: 0 } : { opacity: 0, y: -6 }}
      transition={soft}
      onDragEnd={onDragEnd}
      as="div"
    >
      <ExerciseEditorRow
        pde={pde}
        name={name}
        muscle={muscle}
        intensityMode={intensityMode}
        dragControls={controls}
        onUpdate={onUpdate}
        onDelete={onDelete}
      />
    </Reorder.Item>
  );
}

/**
 * Inline-editable name field (slot name in the canvas header; program name in the
 * page header). Commits on blur / Enter, reverts an empty value (or Escape) to the
 * previous name. Key it by the underlying id at the call site so the draft resets
 * when the target changes.
 */
function InlineNameField({
  name,
  onRename,
  className = "t ew-slot-name",
  ariaLabel = "Slot name",
}: {
  name: string;
  onRename: (name: string) => void;
  className?: string;
  ariaLabel?: string;
}) {
  const [draft, setDraft] = useState(name);
  // Escape blurs to revert, but blur() fires onBlur synchronously (with the typed
  // draft still captured), so guard the commit to actually discard on Escape.
  const skipCommit = useRef(false);
  useEffect(() => {
    setDraft(name);
  }, [name]);

  const commit = () => {
    if (skipCommit.current) {
      skipCommit.current = false;
      setDraft(name);
      return;
    }
    const next = draft.trim();
    if (!next) {
      setDraft(name);
      return;
    }
    if (next !== name) onRename(next);
  };

  return (
    <input
      aria-label={ariaLabel}
      className={className}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
        if (e.key === "Escape") {
          skipCommit.current = true;
          e.currentTarget.blur();
        }
      }}
    />
  );
}

/** Compact numeric stepper for the mesocycle length (1–12 microcycles). */
function MesoField({ value, onCommit }: { value: number; onCommit: (value: number) => void }) {
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
