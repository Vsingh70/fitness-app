"use client";

import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { Reorder, useDragControls } from "motion/react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { BlockControl } from "@/components/workouts/block-control";
import { BlockGroup } from "@/components/workouts/block-group";
import { ExerciseCard, type GripDragControls } from "@/components/workouts/exercise-card";
import { ExerciseRail } from "@/components/workouts/exercise-rail";
import { FloatingRestBar } from "@/components/workouts/floating-rest-bar";
import { InSessionActions, type SyncState } from "@/components/workouts/in-session-actions";
import {
  KeyboardShortcuts,
  KeyboardShortcutsSheet,
} from "@/components/workouts/keyboard-shortcuts";
import { NextUpPreview } from "@/components/workouts/next-up-preview";
import { PlateMathStrip } from "@/components/workouts/plate-math";
import { ReadOnlySessionView } from "@/components/workouts/read-only-session";
import { SessionEndBar } from "@/components/workouts/session-end-bar";
import { SessionTimer } from "@/components/workouts/session-timer";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import {
  useChangeProgramTargets,
  useRemoveFromProgram,
  useSessionProgramContext,
  useSwapInProgram,
} from "@/lib/hooks/in-session-program";
import { useMe, useUpdateDefaultRest } from "@/lib/hooks/me";
import {
  useAddExercise,
  useAddSet,
  useDeleteSet,
  useFinishSession,
  useRemoveExercise,
  useReorderExercise,
  useSession,
  useSkipSession,
  useSwapExercise,
  useUpdateSet,
  useUpdateWorkoutExercise,
} from "@/lib/hooks/workouts";
import { useReducedMotionSafe } from "@/lib/motion/use-reduced-motion-safe";
import { useActiveSession } from "@/lib/state/active-session";
import {
  blockCountsAsVolume,
  type BlockKind,
  type SetCreate,
  type WorkoutExercise,
} from "@/lib/workouts/types";

const ExercisePicker = dynamic(
  () => import("@/components/workouts/exercise-picker").then((m) => m.ExercisePicker),
  { ssr: false },
);

const FALLBACK_REST_SECONDS = 90;

function lastWeightKg(we: WorkoutExercise): number | null {
  for (let i = we.sets.length - 1; i >= 0; i -= 1) {
    const w = we.sets[i]!.weight_kg;
    if (w !== null && w !== undefined) {
      const n = typeof w === "number" ? w : Number(w);
      if (Number.isFinite(n) && n > 0) return n;
    }
  }
  return null;
}

interface ExerciseBlock {
  kind: BlockKind;
  label: string | null;
  exercises: WorkoutExercise[];
}

/**
 * Group session exercises into contiguous runs sharing the same `block_kind`
 * (06 §3c), preserving document order. A run breaks when the kind changes or a
 * non-empty `block_label` differs, so "Mobility" and "Cooldown" warm-up groups
 * render under their own headers.
 */
function groupIntoBlocks(exercises: WorkoutExercise[]): ExerciseBlock[] {
  const blocks: ExerciseBlock[] = [];
  for (const we of exercises) {
    const last = blocks[blocks.length - 1];
    const label = we.block_label ?? null;
    if (last && last.kind === we.block_kind && last.label === label) {
      last.exercises.push(we);
    } else {
      blocks.push({ kind: we.block_kind, label, exercises: [we] });
    }
  }
  return blocks;
}

/**
 * Rebuild the flat exercise list after an in-block reorder. Replaces the
 * block's slice in `flat` with `newBlockOrder`, preserving exercises from
 * other blocks. `blockExercises` identifies which ids belong to this block.
 */
function reorderBlock(
  flat: WorkoutExercise[],
  blockExercises: WorkoutExercise[],
  newBlockOrder: WorkoutExercise[],
): WorkoutExercise[] {
  const blockIds = new Set(blockExercises.map((e) => e.id));
  const result: WorkoutExercise[] = [];
  let inserted = false;
  for (const ex of flat) {
    if (blockIds.has(ex.id)) {
      if (!inserted) {
        result.push(...newBlockOrder);
        inserted = true;
      }
      // old entry dropped; newBlockOrder already pushed above
    } else {
      result.push(ex);
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Drag-reorder primitives — live in this file so they can call useDragControls.
// Only this one file imports motion/react; exercise-card.tsx stays motion-free.
// ---------------------------------------------------------------------------

function SessionExerciseItem({
  we,
  reduced,
  onDragEnd,
  children,
}: {
  we: WorkoutExercise;
  reduced: boolean;
  onDragEnd: () => void;
  children: (controls: GripDragControls) => ReactNode;
}) {
  const controls = useDragControls();
  return (
    <Reorder.Item
      value={we}
      dragListener={false}
      dragControls={controls}
      layout={reduced ? undefined : "position"}
      onDragEnd={onDragEnd}
      as="div"
    >
      {children(controls)}
    </Reorder.Item>
  );
}

function SessionExerciseGroup({
  exercises,
  onReorder,
  className,
  children,
}: {
  exercises: WorkoutExercise[];
  onReorder: (newOrder: WorkoutExercise[]) => void;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Reorder.Group axis="y" values={exercises} onReorder={onReorder} as="div" className={className}>
      {children}
    </Reorder.Group>
  );
}

export default function WorkoutDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  const session = useSession(id);
  const me = useMe();
  const setActive = useActiveSession((s) => s.setActive);
  const clearActive = useActiveSession((s) => s.clearActive);

  const addExercise = useAddExercise(id);
  const addSet = useAddSet(id);
  const updateSet = useUpdateSet(id);
  const deleteSet = useDeleteSet(id);
  const removeExercise = useRemoveExercise(id);
  const reorderExercise = useReorderExercise(id);
  const finishSession = useFinishSession(id);
  const skipSession = useSkipSession(id);
  const swapExercise = useSwapExercise(id);
  const updateWorkoutExercise = useUpdateWorkoutExercise(id);
  const updateDefaultRest = useUpdateDefaultRest();
  const { reduced } = useReducedMotionSafe();

  // Active-program slot behind this session, for "Change / Swap / Remove in
  // program" (05 §3). Resolves to nulls for freestyle sessions.
  const programCtx = useSessionProgramContext(session.data);
  const programId = programCtx.program?.id ?? null;
  const changeProgramTargets = useChangeProgramTargets(programId);
  const swapInProgram = useSwapInProgram(programId);
  const removeFromProgram = useRemoveFromProgram(programId);

  const [pickerOpen, setPickerOpen] = useState(false);
  // What the next exercise pick does: add a new exercise, swap the row for this
  // session only (05 §2), or swap the row in the program (05 §3). `null` rows
  // mean "add". The id is the session workout-exercise being acted on.
  const [pickerMode, setPickerMode] = useState<
    { kind: "add" } | { kind: "swap-session"; id: string } | { kind: "swap-program"; id: string }
  >({ kind: "add" });
  // Which block to assign the exercise to when the picker is in "add" mode.
  const [pickerBlockKind, setPickerBlockKind] = useState<BlockKind>("working");
  // When non-null, the in-session divergence menu (05) is open for this row.
  const [actionsForId, setActionsForId] = useState<string | null>(null);
  const [programSyncState, setProgramSyncState] = useState<SyncState>("idle");
  const [activeWorkoutExerciseId, setActiveWorkoutExerciseId] = useState<string | null>(null);
  const [restKey, setRestKey] = useState<number | null>(null);
  // The session's current rest default (06 §4). Seeded from the user preference;
  // adjustable mid-workout, applies to every subsequent rest in this session.
  const [sessionRest, setSessionRest] = useState<number | null>(null);
  const [restTotal, setRestTotal] = useState(FALLBACK_REST_SECONDS);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [editMode, setEditMode] = useState(false);
  // Local mirror of workout_exercises order so drag-reorders don't snap back
  // before the server confirms. Synced from server on every data change.
  const [localExercises, setLocalExercises] = useState<WorkoutExercise[]>([]);
  const localExercisesRef = useRef<WorkoutExercise[]>([]);
  // Keep the ref current on every render (for use inside drag-end callbacks).
  localExercisesRef.current = localExercises;

  // Seed the session rest default from the user preference once it loads.
  const userDefaultRest = me.data?.default_rest_seconds ?? FALLBACK_REST_SECONDS;
  const unit = me.data?.unit_system;
  useEffect(() => {
    if (sessionRest === null && me.data) setSessionRest(userDefaultRest);
  }, [sessionRest, me.data, userDefaultRest]);
  const activeRest = sessionRest ?? userDefaultRest;

  useEffect(() => {
    if (session.data && !session.data.ended_at) {
      setActive(session.data.id, session.data.started_at);
    }
  }, [session.data, setActive]);

  // Sync local order mirror from server whenever session data changes (including
  // after a reorder mutation invalidates the cache and refetches).
  useEffect(() => {
    if (session.data) {
      setLocalExercises(session.data.workout_exercises);
    }
  }, [session.data]);

  const exerciseIds = useMemo(
    () => (session.data ? session.data.workout_exercises.map((we) => we.exercise_id) : []),
    [session.data],
  );

  const exercisesQuery = useExerciseMeta(exerciseIds);

  // Keep activeWorkoutExerciseId in sync with the session's exercises.
  useEffect(() => {
    const wes = session.data?.workout_exercises ?? [];
    if (wes.length === 0) {
      if (activeWorkoutExerciseId !== null) setActiveWorkoutExerciseId(null);
      return;
    }
    if (activeWorkoutExerciseId && wes.some((we) => we.id === activeWorkoutExerciseId)) return;
    setActiveWorkoutExerciseId(wes[0]!.id);
  }, [session.data?.workout_exercises, activeWorkoutExerciseId]);

  const scrollToExercise = useCallback((workoutExerciseId: string) => {
    if (typeof document === "undefined") return;
    const target = document.querySelector<HTMLElement>(
      `[data-workout-exercise-id="${workoutExerciseId}"]`,
    );
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  const selectExercise = useCallback(
    (workoutExerciseId: string) => {
      setActiveWorkoutExerciseId(workoutExerciseId);
      scrollToExercise(workoutExerciseId);
    },
    [scrollToExercise],
  );

  // ---------------------------------------------------------------------------
  // FIX 2: Memoize derived data and per-exercise handlers so React.memo on
  // ExerciseCard can bail out on unrelated re-renders (e.g. setRestKey ticks).
  // All of these MUST live before the early returns — hooks cannot appear after
  // a conditional return statement.
  // ---------------------------------------------------------------------------

  // isFinished is needed by several memos below; compute it unconditionally.
  const isFinished = !!session.data?.ended_at;

  // Stable reference for the display list: prefers local drag-order mirror,
  // falls back to server data. Wrapped in useMemo so the array identity is
  // preserved across renders when neither source changes (prevents downstream
  // memos from re-running unnecessarily).
  const displayExercises = useMemo(
    () => (localExercises.length > 0 ? localExercises : (session.data?.workout_exercises ?? [])),
    [localExercises, session.data],
  );

  // Maps rebuilt only when session data changes, not on every render.
  const targetSetsById = useMemo(() => {
    const m = new Map<string, number | null>();
    for (const we of session.data?.workout_exercises ?? []) {
      m.set(we.id, null);
    }
    return m;
  }, [session.data]);

  const exerciseNames = useMemo(() => {
    const m = new Map<string, string>();
    for (const we of session.data?.workout_exercises ?? []) {
      m.set(we.exercise_id, exercisesQuery.data?.get(we.exercise_id)?.name ?? "Exercise");
    }
    return m;
  }, [session.data, exercisesQuery.data]);

  // Block grouping: only recomputes when the display list changes.
  const blocks = useMemo(() => groupIntoBlocks(displayExercises), [displayExercises]);

  // Destructure stable mutation functions so useMemo deps don't see a new
  // object reference on every render (TanStack Query v5 keeps mutateAsync
  // stable via useCallback internally).
  const { mutateAsync: addSetAsync } = addSet;
  const { mutateAsync: updateSetAsync } = updateSet;
  const { mutateAsync: deleteSetAsync } = deleteSet;
  const { mutateAsync: removeExerciseAsync } = removeExercise;
  const { mutate: updateWeMutate, isPending: updateWeIsPending } = updateWorkoutExercise;

  // Per-exercise handler map: stable as long as the exercise list, the mutation
  // functions, isFinished, and activeRest don't change. Critically, a
  // setRestKey(Date.now()) tick touches none of these → map stays the same
  // reference → ExerciseCard memo bails out for every unrelated card.
  const handlersByWeId = useMemo(() => {
    const m = new Map<
      string,
      {
        onAddSet: (body: SetCreate) => Promise<void>;
        onUpdateSet: (setId: string, body: SetCreate) => Promise<void>;
        onDeleteSet: (setId: string) => Promise<void>;
        onRemoveExercise: () => Promise<void>;
        onMoreActions: () => void;
      }
    >();
    for (const we of displayExercises) {
      const weId = we.id;
      m.set(weId, {
        onAddSet: async (body) => {
          await addSetAsync({ workoutExerciseId: weId, body });
          if (!isFinished) {
            setRestTotal(activeRest);
            setRestKey(Date.now());
          }
        },
        onUpdateSet: async (setId, body) => {
          // Edit an already-logged set in place; never appends a duplicate, and
          // editing a past set does not restart the rest timer.
          await updateSetAsync({ setId, body });
        },
        onDeleteSet: async (setId) => {
          await deleteSetAsync(setId);
        },
        onRemoveExercise: async () => {
          await removeExerciseAsync(weId);
        },
        onMoreActions: () => {
          setProgramSyncState("idle");
          setActionsForId(weId);
        },
      });
    }
    return m;
  }, [
    displayExercises,
    addSetAsync,
    updateSetAsync,
    deleteSetAsync,
    removeExerciseAsync,
    isFinished,
    activeRest,
  ]);

  // Per-exercise blockControl ReactNodes: stable across renders that don't
  // change the exercise list, isFinished, or the update-exercise mutation state.
  const blockControlsByWeId = useMemo(() => {
    const m = new Map<string, ReactNode>();
    if (isFinished) return m;
    for (const we of displayExercises) {
      const weId = we.id;
      m.set(
        weId,
        <BlockControl
          kind={we.block_kind}
          label={we.block_label}
          disabled={updateWeIsPending}
          onChange={(body) => updateWeMutate({ workoutExerciseId: weId, body })}
        />,
      );
    }
    return m;
  }, [displayExercises, isFinished, updateWeIsPending, updateWeMutate]);

  if (session.isLoading) return <p className="text-text-secondary">Loading session…</p>;
  if (session.isError) return <p className="text-destructive">Could not load session.</p>;
  if (!session.data) return null;

  const s = session.data;
  const showReadOnly = isFinished && !editMode;

  const onFinish = () => {
    finishSession.mutate(undefined, {
      onSuccess: () => {
        clearActive();
        router.push(`/workouts/${s.id}/summary`);
      },
    });
  };

  const onSkip = () => {
    skipSession.mutate(undefined, {
      onSuccess: () => {
        clearActive();
        router.push("/workouts");
      },
    });
  };

  const activeIdx = activeWorkoutExerciseId
    ? s.workout_exercises.findIndex((we) => we.id === activeWorkoutExerciseId)
    : -1;
  const activeWe = activeIdx >= 0 ? s.workout_exercises[activeIdx] : null;
  const nextWe = activeIdx >= 0 ? s.workout_exercises[activeIdx + 1] : null;
  const actionsWe = actionsForId
    ? (s.workout_exercises.find((we) => we.id === actionsForId) ?? null)
    : null;

  const nextExercise = () => {
    if (s.workout_exercises.length === 0) return;
    const i = activeIdx >= 0 ? activeIdx : 0;
    const j = Math.min(s.workout_exercises.length - 1, i + 1);
    selectExercise(s.workout_exercises[j]!.id);
  };
  const prevExercise = () => {
    if (s.workout_exercises.length === 0) return;
    const i = activeIdx >= 0 ? activeIdx : 0;
    const j = Math.max(0, i - 1);
    selectExercise(s.workout_exercises[j]!.id);
  };
  const toggleRest = () => {
    if (restKey === null) {
      setRestTotal(activeRest);
      setRestKey(Date.now());
    } else setRestKey(null);
  };

  // Plate math only for barbell weight_reps exercises with a previous weight.
  const activeExerciseMeta = activeWe ? exercisesQuery.data?.get(activeWe.exercise_id) : undefined;
  const plateTargetKg =
    activeWe &&
    activeExerciseMeta?.equipment === "barbell" &&
    activeExerciseMeta.tracking_type === "weight_reps"
      ? lastWeightKg(activeWe)
      : null;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5 pb-32">
      {!showReadOnly ? (
        <KeyboardShortcuts
          onAddExercise={() => setPickerOpen(true)}
          onShowHelp={() => setShortcutsOpen(true)}
          onNextExercise={nextExercise}
          onPrevExercise={prevExercise}
          onToggleRest={toggleRest}
        />
      ) : null}

      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
            {isFinished ? "Finished" : "In progress"}
          </span>
          <h1 className="mt-1 font-serif text-2xl font-medium tracking-tight">
            {s.name ?? "Workout"}
          </h1>
          <SessionTimer
            startedAtMs={new Date(s.started_at).getTime()}
            endedAtMs={s.ended_at ? new Date(s.ended_at).getTime() : null}
            className="text-text-secondary mt-1 block font-serif text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          {!showReadOnly ? (
            <button
              type="button"
              onClick={() => setShortcutsOpen(true)}
              className="text-text-secondary hover:text-text border-border-strong inline-flex h-[32px] items-center rounded-[var(--radius-pill)] border px-3 text-[11px] font-semibold tracking-[0.08em] uppercase"
              title="Keyboard shortcuts (?)"
            >
              ?
            </button>
          ) : null}
          {isFinished ? (
            <>
              <Button
                type="button"
                variant={editMode ? "primary" : "secondary"}
                size="sm"
                onClick={() => setEditMode((v) => !v)}
              >
                {editMode ? "Done editing" : "Edit"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => router.push(`/workouts/${s.id}/summary`)}
              >
                Summary
              </Button>
            </>
          ) : (
            <>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onSkip}
                disabled={skipSession.isPending}
                data-testid="skip-workout"
              >
                {skipSession.isPending ? "Skipping…" : "Skip"}
              </Button>
              <Button
                type="button"
                onClick={onFinish}
                disabled={finishSession.isPending}
                data-testid="finish-workout"
              >
                {finishSession.isPending ? "Finishing…" : "Finish"}
              </Button>
            </>
          )}
        </div>
      </header>

      {!showReadOnly && s.workout_exercises.length > 0 ? (
        <ExerciseRail
          workoutExercises={s.workout_exercises}
          exerciseNames={exerciseNames}
          targetSetsById={targetSetsById}
          activeId={activeWorkoutExerciseId}
          onSelect={selectExercise}
        />
      ) : null}

      {!showReadOnly && plateTargetKg !== null ? <PlateMathStrip targetKg={plateTargetKg} /> : null}

      {showReadOnly ? (
        <ReadOnlySessionView
          workoutExercises={s.workout_exercises}
          exerciseMeta={exercisesQuery.data ?? new Map()}
          unit={unit}
        />
      ) : displayExercises.length === 0 ? (
        <Card>
          <CardContent>
            <p className="text-text-secondary">No exercises yet. Add one to start logging sets.</p>
          </CardContent>
        </Card>
      ) : (
        blocks.map((block, bi) => {
          // On reorder: rebuild the flat list with the block's new order, update
          // the ref synchronously (so onDragEnd sees the final position immediately),
          // then trigger a re-render with the new state.
          const handleBlockReorder = (newBlockOrder: WorkoutExercise[]) => {
            const next = reorderBlock(localExercisesRef.current, block.exercises, newBlockOrder);
            localExercisesRef.current = next;
            setLocalExercises(next);
          };

          // On drop: find the moved exercise's new global index in the flat list
          // (already updated by handleBlockReorder) and call the API once.
          const handleDragEnd = (weId: string) => {
            const position = localExercisesRef.current.findIndex((e) => e.id === weId);
            if (position >= 0) {
              reorderExercise.mutate({ workoutExerciseId: weId, position });
            }
          };

          const items = block.exercises.map((we) => {
            const exMeta = exercisesQuery.data?.get(we.exercise_id);
            // Pull stable handler refs from the memoized map so ExerciseCard's
            // React.memo sees the same function references across re-renders
            // (e.g. setRestKey ticks) that don't change the exercise list.
            const handlers = handlersByWeId.get(we.id)!;
            return (
              <SessionExerciseItem
                key={we.id}
                we={we}
                reduced={reduced}
                onDragEnd={() => handleDragEnd(we.id)}
              >
                {(controls) => (
                  <ExerciseCard
                    workoutExercise={we}
                    exerciseName={exMeta?.name ?? "Exercise"}
                    trackingType={exMeta?.tracking_type ?? "weight_reps"}
                    nonVolume={!blockCountsAsVolume(we.block_kind)}
                    unit={unit}
                    substitutedFor={
                      we.substituted_for_exercise_id
                        ? (exerciseNames.get(we.substituted_for_exercise_id) ?? "original")
                        : null
                    }
                    blockControl={blockControlsByWeId.get(we.id)}
                    onAddSet={handlers.onAddSet}
                    onUpdateSet={handlers.onUpdateSet}
                    onDeleteSet={handlers.onDeleteSet}
                    onRemoveExercise={handlers.onRemoveExercise}
                    onMoreActions={isFinished ? undefined : handlers.onMoreActions}
                    dragControls={controls}
                  />
                )}
              </SessionExerciseItem>
            );
          });

          // A lone all-working session needs no block chrome; render bare.
          if (block.kind === "working" && !block.label) {
            return (
              <SessionExerciseGroup
                key={`block-${bi}`}
                exercises={block.exercises}
                onReorder={handleBlockReorder}
                className="flex flex-col gap-5"
              >
                {items}
              </SessionExerciseGroup>
            );
          }
          return (
            <BlockGroup
              key={`block-${bi}`}
              kind={block.kind}
              label={block.label}
              count={block.exercises.length}
            >
              <SessionExerciseGroup
                exercises={block.exercises}
                onReorder={handleBlockReorder}
                className="flex flex-col gap-4"
              >
                {items}
              </SessionExerciseGroup>
            </BlockGroup>
          );
        })
      )}

      {!showReadOnly && !isFinished && nextWe ? (
        <NextUpPreview
          name={exerciseNames.get(nextWe.exercise_id) ?? "Exercise"}
          trackingType={
            exercisesQuery.data?.get(nextWe.exercise_id)?.tracking_type ?? "weight_reps"
          }
          onSkipAhead={() => selectExercise(nextWe.id)}
        />
      ) : null}

      {!showReadOnly && !isFinished ? (
        <div className="flex flex-col gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setPickerBlockKind("working");
              setPickerOpen(true);
            }}
            data-testid="add-exercise"
          >
            + Add exercise
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setPickerBlockKind("warmup");
              setPickerOpen(true);
            }}
            data-testid="add-warmup"
          >
            + Add warm-up
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setPickerBlockKind("cooldown");
              setPickerOpen(true);
            }}
            data-testid="add-cooldown"
          >
            + Add cooldown
          </Button>
        </div>
      ) : null}

      <ExercisePicker
        open={pickerOpen}
        onOpenChange={(open) => {
          setPickerOpen(open);
          if (!open) {
            setPickerMode({ kind: "add" });
            setPickerBlockKind("working");
          }
        }}
        initialMovementPattern={
          pickerBlockKind === "warmup" || pickerBlockKind === "cooldown" ? "mobility" : undefined
        }
        onPick={(ex) => {
          if (pickerMode.kind === "swap-session") {
            swapExercise.mutate({
              workoutExerciseId: pickerMode.id,
              substituteExerciseId: ex.id,
            });
          } else if (pickerMode.kind === "swap-program") {
            // A program swap rewrites the active slot now + forward. The
            // in-progress session is left as-is (logged sets stand, 05 §3); the
            // user keeps logging the current movement this session.
            const we = s.workout_exercises.find((w) => w.id === pickerMode.id);
            const pde = we ? programCtx.slotExerciseFor(we.exercise_id) : null;
            if (programCtx.slot && pde) {
              setProgramSyncState("saving");
              swapInProgram.mutate(
                {
                  slotId: programCtx.slot.id,
                  pde,
                  substituteExerciseId: ex.id,
                },
                {
                  onSuccess: () => setProgramSyncState("synced"),
                  onError: () => setProgramSyncState("error"),
                },
              );
            }
          } else {
            addExercise.mutate({ exercise_id: ex.id, block_kind: pickerBlockKind });
          }
          setPickerMode({ kind: "add" });
          setPickerBlockKind("working");
        }}
      />

      {actionsWe ? (
        <InSessionActions
          open={actionsForId !== null}
          onOpenChange={(open) => {
            if (!open) setActionsForId(null);
          }}
          exerciseName={exerciseNames.get(actionsWe.exercise_id) ?? "Exercise"}
          slotExercise={programCtx.slotExerciseFor(actionsWe.exercise_id)}
          intensityMode={programCtx.program?.intensity_mode ?? "off"}
          programSyncState={programSyncState}
          onSwapForSession={() => {
            setPickerMode({ kind: "swap-session", id: actionsWe.id });
            setPickerOpen(true);
          }}
          onSwapInProgram={() => {
            setPickerMode({ kind: "swap-program", id: actionsWe.id });
            setPickerOpen(true);
          }}
          onChangeTargets={(body) => {
            const pde = programCtx.slotExerciseFor(actionsWe.exercise_id);
            if (!pde) return;
            setProgramSyncState("saving");
            changeProgramTargets.mutate(
              { pdeId: pde.id, body },
              {
                onSuccess: () => setProgramSyncState("synced"),
                onError: () => setProgramSyncState("error"),
              },
            );
          }}
          onRemoveFromProgram={() => {
            const pde = programCtx.slotExerciseFor(actionsWe.exercise_id);
            if (!pde) return;
            setProgramSyncState("saving");
            removeFromProgram.mutate(pde.id, {
              onSuccess: () => setProgramSyncState("synced"),
              onError: () => setProgramSyncState("error"),
            });
          }}
          onRemoveFromSession={() => {
            void removeExercise.mutateAsync(actionsWe.id);
          }}
        />
      ) : null}

      <KeyboardShortcutsSheet open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />

      {!showReadOnly && !isFinished ? (
        <SessionEndBar
          finishing={finishSession.isPending}
          skipping={skipSession.isPending}
          onFinish={onFinish}
          onSkip={onSkip}
        />
      ) : null}

      {!showReadOnly ? (
        <FloatingRestBar
          activeKey={restKey}
          totalSeconds={restTotal}
          defaultSeconds={activeRest}
          onStart={() => {
            setRestTotal(activeRest);
            setRestKey(Date.now());
          }}
          onSkip={() => setRestKey(null)}
          onChangeDefault={(seconds) => setSessionRest(seconds)}
          onSaveDefault={(seconds) => updateDefaultRest.mutate(seconds)}
          savingDefault={updateDefaultRest.isPending}
        />
      ) : null}
    </div>
  );
}
