"use client";

import { GripVertical, Plus, Trash2 } from "lucide-react";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { PeriodizationControl } from "@/components/programs/periodization-control";
import { VolumeSummary } from "@/components/programs/volume-summary";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
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
import type {
  PeriodizationMode,
  ProgramDayExercise,
  ProgramDayExerciseUpdate,
} from "@/lib/programs/types";

const ExercisePicker = dynamic(
  () => import("@/components/workouts/exercise-picker").then((m) => m.ExercisePicker),
  { ssr: false },
);

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function ProgramEditorPage() {
  const { id } = useParams<{ id: string }>();
  const program = useProgram(id);

  const updateProgram = useUpdateProgram(id);
  const addDay = useAddDay(id);
  const deleteDay = useDeleteDay(id);
  const addExercise = useAddExerciseToDay(id);
  const updateExercise = useUpdateProgramExercise(id);
  const deleteExercise = useDeleteProgramExercise(id);
  const activate = useActivateProgram(id);
  const deactivate = useDeactivateProgram(id);
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

  if (program.isLoading) return <p className="text-text-secondary">Loading program...</p>;
  if (program.isError || !program.data)
    return <p className="text-destructive">Could not load program.</p>;

  const p = program.data;
  const day = p.days[Math.min(currentDayIdx, p.days.length - 1)];
  const isContinuous = p.periodization_mode === "continuous";

  const setMode = (mode: PeriodizationMode) => {
    if (mode === p.periodization_mode) return;
    updateProgram.mutate({ periodization_mode: mode });
  };
  const setAutoDeloadOnStall = (value: boolean) => {
    updateProgram.mutate({ auto_deload_on_stall: value });
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-text-tertiary text-xs">Programs ›</p>
          <h1 className="font-serif text-[32px] leading-tight font-medium tracking-tight">
            {p.name}
          </h1>
          <p className="text-text-tertiary mt-1 text-xs capitalize">
            {p.goal} ·{" "}
            {isContinuous
              ? `${p.days_per_week} days/week · Ongoing`
              : `${p.weeks} weeks × ${p.days_per_week} days/week`}
            {p.is_active ? " · Active" : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {p.is_active ? (
            <Button
              type="button"
              variant="secondary"
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

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        {/* Left rail: program meta + weekly volume */}
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <span>Program details</span>
            </CardHeader>
            <CardContent className="flex flex-col gap-3.5">
              <PeriodizationControl
                mode={p.periodization_mode}
                onChange={setMode}
                autoDeloadOnStall={p.auto_deload_on_stall}
                onAutoDeloadOnStallChange={setAutoDeloadOnStall}
                disabled={updateProgram.isPending}
              />
              <Field label="Goal">
                <span className="text-text text-sm capitalize">{p.goal}</span>
              </Field>
              <div className="grid grid-cols-2 gap-2.5">
                {isContinuous ? null : (
                  <Field label="Weeks">
                    <span className="text-text font-serif text-sm tabular-nums">{p.weeks}</span>
                  </Field>
                )}
                <Field label="Days / week">
                  <span className="text-text font-serif text-sm tabular-nums">
                    {p.days_per_week}
                  </span>
                </Field>
              </div>
              <Field label="Status">
                {p.is_active ? (
                  <span className="text-accent inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)] px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
                    Active
                  </span>
                ) : (
                  <span className="text-text-secondary border-border-strong inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
                    Draft
                  </span>
                )}
              </Field>
            </CardContent>
          </Card>

          <VolumeSummary program={p} exercises={exMeta.data ?? new Map()} />
        </div>

        {/* Right: day rail + day editor */}
        <div className="flex min-w-0 flex-col gap-4">
          <div className="bg-surface border-border flex gap-1 overflow-x-auto rounded-[12px] border p-1">
            {p.days.map((d, idx) => {
              const active = idx === currentDayIdx;
              return (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => setCurrentDayIdx(idx)}
                  className={`inline-flex items-center gap-2 rounded-[8px] px-[14px] py-2.5 text-[13px] whitespace-nowrap transition-colors duration-150 ease-out ${
                    active
                      ? "bg-surface-elevated text-text font-semibold shadow-[var(--shadow-1)]"
                      : "text-text-secondary hover:text-text font-medium"
                  }`}
                >
                  {d.name}
                  <span className="text-text-tertiary text-[10px] tabular-nums">
                    {d.exercises.length}
                  </span>
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => {
                addDay.mutate({ name: `Day ${p.days.length + 1}` });
                setCurrentDayIdx(p.days.length);
              }}
              className="border-border-strong text-accent inline-flex items-center gap-1 rounded-[8px] border border-dashed px-[14px] py-2.5 text-[13px] font-semibold whitespace-nowrap"
            >
              <Plus className="h-3.5 w-3.5" /> Day
            </button>
          </div>

          {day ? (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="font-serif text-lg font-medium tracking-tight">{day.name}</h2>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => deleteDay.mutate(day.id)}
                  aria-label="Delete day"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>

              {day.exercises.length === 0 ? (
                <Card>
                  <CardContent>
                    <p className="text-text-secondary text-sm">No exercises yet.</p>
                  </CardContent>
                </Card>
              ) : (
                day.exercises.map((pde) => {
                  const meta = exMeta.data?.get(pde.exercise_id);
                  return (
                    <Card key={pde.id} className="p-4">
                      <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3">
                        <span
                          className="text-text-tertiary grid h-7 w-7 place-items-center rounded-md"
                          aria-hidden
                        >
                          <GripVertical className="h-3.5 w-3.5" />
                        </span>
                        <div className="min-w-0">
                          <div className="text-text truncate text-[15px] font-semibold">
                            {meta?.name ?? "Exercise"}
                          </div>
                          <div className="mt-0.5 flex flex-wrap gap-1.5">
                            {meta?.primary_muscle ? (
                              <Tag>{meta.primary_muscle.replace(/_/g, " ")}</Tag>
                            ) : null}
                            {meta?.equipment ? <Tag>{meta.equipment}</Tag> : null}
                          </div>
                        </div>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          aria-label="Delete exercise"
                          onClick={() => deleteExercise.mutate(pde.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      <ExerciseTargetsEditor
                        pde={pde}
                        onUpdate={(body) =>
                          updateExercise.mutate(
                            { pdeId: pde.id, body },
                            {
                              onError: () =>
                                pushToast({
                                  kind: "error",
                                  message: "Could not update exercise targets.",
                                }),
                            },
                          )
                        }
                      />
                    </Card>
                  );
                })
              )}

              <button
                type="button"
                onClick={() => setPickerOpenForDay(day.id)}
                className="border-border-strong text-accent hover:bg-accent-soft hover:border-accent flex items-center justify-center gap-2 rounded-[12px] border border-dashed px-4 py-3.5 text-sm font-semibold transition-[background-color,border-color] duration-150 ease-out"
              >
                <Plus className="h-[18px] w-[18px]" /> Add exercise to {day.name}
              </button>
            </div>
          ) : null}
        </div>
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
              body: { exercise_id: ex.id, target_sets: 3, progression_strategy: "none" },
            });
            setPickerOpenForDay(null);
          }
        }}
      />

      <ActivateSheet
        open={activateOpen}
        onOpenChange={setActivateOpen}
        onActivate={(req) =>
          activate.mutate(req, {
            onSuccess: () => setActivateOpen(false),
          })
        }
        isPending={activate.isPending}
      />
    </div>
  );
}

/**
 * Per-exercise target controls. Rep semantics: only "low" filled = fixed rep
 * goal ("5"); both filled = range ("8 – 12"). Commits on blur/Enter and never
 * sends a pair with high < low — the counterpart bound is adjusted instead.
 */
function ExerciseTargetsEditor({
  pde,
  onUpdate,
}: {
  pde: ProgramDayExercise;
  onUpdate: (body: ProgramDayExerciseUpdate) => void;
}) {
  return (
    <div className="mt-3 flex flex-wrap items-end gap-3">
      <NumberField
        label="Sets"
        value={pde.target_sets}
        min={1}
        max={20}
        onCommit={(n) => {
          if (n !== null) onUpdate({ target_sets: n });
        }}
      />
      <NumberField
        label="Reps low"
        value={pde.target_reps_low}
        min={1}
        max={100}
        allowEmpty
        onCommit={(n) => {
          const body: ProgramDayExerciseUpdate = { target_reps_low: n };
          // Clearing the low bound clears the range; raising it above the
          // high bound collapses the range to a fixed goal.
          if (n === null) body.target_reps_high = null;
          else if (pde.target_reps_high !== null && pde.target_reps_high < n)
            body.target_reps_high = n;
          onUpdate(body);
        }}
      />
      <NumberField
        label="Reps high"
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
      <NumberField
        label="Rest (sec)"
        value={pde.rest_seconds}
        min={1}
        max={3600}
        allowEmpty
        onCommit={(n) => onUpdate({ rest_seconds: n })}
      />
    </div>
  );
}

/** Compact numeric input that commits on blur/Enter; invalid input reverts. */
function NumberField({
  label,
  value,
  min,
  max,
  allowEmpty = false,
  onCommit,
}: {
  label: string;
  value: number | null;
  min: number;
  max: number;
  allowEmpty?: boolean;
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
    <label className="flex flex-col gap-1">
      <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
        {label}
      </span>
      <Input
        aria-label={label}
        type="number"
        min={min}
        max={max}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
        }}
        className="h-9 w-20 tabular-nums"
      />
    </label>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
        {label}
      </span>
      {children}
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-text-secondary border-border-strong inline-flex h-[20px] items-center rounded-[var(--radius-pill)] border px-2 text-[10px] font-medium capitalize">
      {children}
    </span>
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
          {isPending ? "Activating..." : "Activate"}
        </Button>
      </div>
    </Sheet>
  );
}
