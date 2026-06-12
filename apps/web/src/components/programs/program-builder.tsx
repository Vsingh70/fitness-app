"use client";

import { GripVertical } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";

import { ExerciseEditorRow } from "@/components/programs/exercise-editor-row";
import { IntensityModeControl } from "@/components/programs/intensity-mode-control";
import { MiniSegmented } from "@/components/programs/mini-segmented";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { useToastStore } from "@/components/ui/toast";
import { useExerciseMeta } from "@/lib/hooks/exercises";
import {
  useActivateProgram,
  useAddDay,
  useAddExerciseToDay,
  useDeactivateProgram,
  useDeleteDay,
  useDeleteProgramExercise,
  useProgram,
  useUpdateProgram,
  useUpdateProgramExercise,
} from "@/lib/hooks/programs";
import { computeVolume } from "@/lib/programs/volume";
import type {
  IntensityMode,
  PeriodizationMode,
  ProgramDayExerciseUpdate,
} from "@/lib/programs/types";

const PERIODIZATION_OPTIONS: readonly { value: PeriodizationMode; label: string }[] = [
  { value: "block", label: "Block" },
  { value: "continuous", label: "Cont." },
];

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const ExercisePicker = dynamic(
  () => import("@/components/workouts/exercise-picker").then((m) => m.ExercisePicker),
  { ssr: false },
);

/**
 * Program builder (`.ew-grid`): a day rail + Details panel on the left and the
 * selected day's exercise list on the right. Reps are per-exercise (Range vs
 * Target); intensity is one program-wide RPE/RIR/Off setting (the Details panel's
 * IntensityModeControl). Every edit is persisted immediately through the program
 * hooks — there is no explicit "save". Periodization and weekly-volume are kept
 * from the shipped editor, restyled into the editorial rail.
 */
export function ProgramBuilder({ programId }: { programId: string }) {
  const program = useProgram(programId);
  const updateProgram = useUpdateProgram(programId);
  const addDay = useAddDay(programId);
  const deleteDay = useDeleteDay(programId);
  const addExercise = useAddExerciseToDay(programId);
  const updateExercise = useUpdateProgramExercise(programId);
  const deleteExercise = useDeleteProgramExercise(programId);
  const activate = useActivateProgram(programId);
  const deactivate = useDeactivateProgram(programId);
  const pushToast = useToastStore((s) => s.push);

  const [currentDayIdx, setCurrentDayIdx] = useState(0);
  const [pickerOpenForDay, setPickerOpenForDay] = useState<string | null>(null);
  const [activateOpen, setActivateOpen] = useState(false);

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
  const day = p.days[Math.min(currentDayIdx, p.days.length - 1)];
  const isContinuous = p.periodization_mode === "continuous";
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

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-text-tertiary text-xs">
            <Link href={`/programs/${p.id}`} className="hover:text-text">
              {p.name}
            </Link>{" "}
            › Edit
          </p>
          <h1 className="font-serif text-[32px] leading-tight font-medium tracking-tight">
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
              onClick={() => setActivateOpen(true)}
              disabled={p.days.length !== p.days_per_week}
            >
              Save &amp; activate
            </Button>
          )}
        </div>
      </header>

      {p.days.length !== p.days_per_week ? (
        <p className="text-warning text-xs">
          Program has {p.days.length} day{p.days.length === 1 ? "" : "s"} but {p.days_per_week} are
          required to activate.
        </p>
      ) : null}

      <div className="ew-grid">
        {/* Left rail: days + details + periodization + intensity + volume */}
        <aside>
          <div className="pw-kicker" style={{ marginBottom: 10 }}>
            Days
          </div>
          <div className="ew-days">
            {p.days.map((d, idx) => (
              <button
                key={d.id}
                type="button"
                className={`ew-dtab ${idx === currentDayIdx ? "on" : ""}`}
                onClick={() => setCurrentDayIdx(idx)}
              >
                <span className="gr" aria-hidden>
                  <GripVertical size={14} />
                </span>
                <span className="nm">{d.name}</span>
                <span className="ct">{d.exercises.length}</span>
              </button>
            ))}
            <button
              type="button"
              className="ew-dtab add"
              onClick={() => {
                addDay.mutate({ name: `Day ${p.days.length + 1}` });
                setCurrentDayIdx(p.days.length);
              }}
            >
              + Add day
            </button>
          </div>

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
            {isContinuous ? null : (
              <div>
                Weeks — <b>{p.weeks}</b>
              </div>
            )}
            <div>
              Days / week — <b>{p.days_per_week}</b>
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
            ) : null}
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

        {/* Right: selected day's exercises */}
        <section className="ew-canvas">
          {day ? (
            <>
              <div className="h">
                <span className="t">{day.name}</span>
                <button
                  type="button"
                  className="pw-link"
                  onClick={() => deleteDay.mutate(day.id)}
                  style={{ color: "var(--color-text-tertiary)" }}
                >
                  Delete day
                </button>
              </div>

              {day.exercises.length === 0 ? (
                <p className="text-text-secondary py-4 text-sm">No exercises yet.</p>
              ) : (
                day.exercises.map((pde) => (
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

              <button type="button" className="ew-add" onClick={() => setPickerOpenForDay(day.id)}>
                + Add exercise to {day.name}
              </button>
            </>
          ) : (
            <p className="text-text-secondary text-sm">Add a day to start building.</p>
          )}
        </section>
      </div>

      <ExercisePicker
        open={pickerOpenForDay !== null}
        onOpenChange={(o) => {
          if (!o) setPickerOpenForDay(null);
        }}
        onPick={(ex) => {
          if (pickerOpenForDay) {
            addExercise.mutate({
              dayId: pickerOpenForDay,
              body: {
                exercise_id: ex.id,
                target_sets: 3,
                progression_strategy: "none",
                rep_mode: "range",
              },
            });
            setPickerOpenForDay(null);
          }
        }}
      />

      <ActivateSheet
        open={activateOpen}
        onOpenChange={setActivateOpen}
        onActivate={(req) => activate.mutate(req, { onSuccess: () => setActivateOpen(false) })}
        isPending={activate.isPending}
      />
    </div>
  );
}

function ActivateSheet({
  open,
  onOpenChange,
  onActivate,
  isPending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onActivate: (body: {
    start_date: string;
    weekday_offset: number;
    skip_existing: boolean;
  }) => void;
  isPending: boolean;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const [startDate, setStartDate] = useState(today);
  const [weekday, setWeekday] = useState(0);

  return (
    <Sheet open={open} onOpenChange={onOpenChange} title="Activate program">
      <div className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Start date</span>
          <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-text-secondary">Day 1 lands on</span>
          <div className="flex flex-wrap gap-1">
            {WEEKDAY_LABELS.map((label, idx) => (
              <button
                key={label}
                type="button"
                onClick={() => setWeekday(idx)}
                className={`inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase ${
                  weekday === idx
                    ? "text-accent border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)]"
                    : "border-border-strong text-text-secondary hover:text-text"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </label>
        <p className="text-text-tertiary text-xs">
          Any other active program will be deactivated; its future workouts get marked skipped.
        </p>
        <Button
          type="button"
          onClick={() =>
            onActivate({ start_date: startDate, weekday_offset: weekday, skip_existing: true })
          }
          disabled={isPending}
        >
          {isPending ? "Activating…" : "Activate"}
        </Button>
      </div>
    </Sheet>
  );
}
