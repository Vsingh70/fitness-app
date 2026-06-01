"use client";

import { useQuery } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { ExercisePicker } from "@/components/workouts/exercise-picker";
import { VolumeSummary } from "@/components/programs/volume-summary";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { searchExercises } from "@/lib/api/workouts";
import {
  useActivateProgram,
  useAddDay,
  useAddExerciseToDay,
  useDeactivateProgram,
  useDeleteDay,
  useDeleteProgramExercise,
  useProgram,
  useUpdateProgramExercise,
} from "@/lib/hooks/programs";
import type { Exercise } from "@/lib/workouts/types";

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function ProgramEditorPage() {
  const { id } = useParams<{ id: string }>();
  const program = useProgram(id);

  const addDay = useAddDay(id);
  const deleteDay = useDeleteDay(id);
  const addExercise = useAddExerciseToDay(id);
  const updateExercise = useUpdateProgramExercise(id);
  const deleteExercise = useDeleteProgramExercise(id);
  const activate = useActivateProgram(id);
  const deactivate = useDeactivateProgram(id);

  const [currentDayIdx, setCurrentDayIdx] = useState(0);
  const [pickerOpenForDay, setPickerOpenForDay] = useState<string | null>(null);
  const [activateOpen, setActivateOpen] = useState(false);

  const exerciseIds = useMemo(
    () =>
      program.data ? program.data.days.flatMap((d) => d.exercises.map((e) => e.exercise_id)) : [],
    [program.data],
  );

  const exMeta = useQuery({
    queryKey: ["exercise-meta", [...exerciseIds].sort().join(",")],
    queryFn: async () => {
      if (exerciseIds.length === 0) return new Map<string, Exercise>();
      const list = await searchExercises(undefined, { limit: 200 });
      const map = new Map<string, Exercise>();
      for (const ex of list.items) if (exerciseIds.includes(ex.id)) map.set(ex.id, ex);
      return map;
    },
    enabled: exerciseIds.length > 0,
    staleTime: 60_000,
  });

  if (program.isLoading) return <p className="text-text-secondary">Loading program...</p>;
  if (program.isError || !program.data)
    return <p className="text-destructive">Could not load program.</p>;

  const p = program.data;
  const day = p.days[Math.min(currentDayIdx, p.days.length - 1)];

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4 lg:flex-row">
      <div className="flex flex-1 flex-col gap-4">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-serif text-[32px] font-medium tracking-tight">{p.name}</h1>
            <p className="text-text-tertiary text-xs">
              {p.goal} - {p.weeks} weeks x {p.days_per_week} days/week
              {p.is_active ? " - Active" : ""}
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
                Activate
              </Button>
            )}
          </div>
        </header>

        {p.days.length !== p.days_per_week ? (
          <p className="text-warning text-xs">
            Program has {p.days.length} day{p.days.length === 1 ? "" : "s"} but {p.days_per_week}{" "}
            are required to activate.
          </p>
        ) : null}

        <div className="flex flex-wrap gap-1">
          {p.days.map((d, idx) => (
            <button
              key={d.id}
              type="button"
              onClick={() => setCurrentDayIdx(idx)}
              className={`inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold uppercase tracking-[0.1em] ${
                idx === currentDayIdx
                  ? "border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)] text-accent"
                  : "border-border-strong text-text-secondary hover:text-text"
              }`}
            >
              Day {idx + 1}: {d.name}
            </button>
          ))}
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => {
              addDay.mutate({ name: `Day ${p.days.length + 1}` });
              setCurrentDayIdx(p.days.length);
            }}
          >
            + Day
          </Button>
        </div>

        {day ? (
          <Card>
            <CardHeader className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">{day.name}</h2>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => deleteDay.mutate(day.id)}
                aria-label="Delete day"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {day.exercises.length === 0 ? (
                <p className="text-text-secondary text-sm">No exercises yet.</p>
              ) : (
                day.exercises.map((pde) => {
                  const meta = exMeta.data?.get(pde.exercise_id);
                  return (
                    <div
                      key={pde.id}
                      className="border-border flex items-center justify-between border-t pt-2 first:border-t-0 first:pt-0"
                    >
                      <div className="flex flex-col text-sm">
                        <span className="text-text font-medium">{meta?.name ?? "Exercise"}</span>
                        <span className="text-text-tertiary text-xs">
                          {meta?.primary_muscle} - {meta?.equipment}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Input
                          aria-label="Target sets"
                          type="number"
                          min={1}
                          max={20}
                          value={pde.target_sets}
                          onChange={(e) =>
                            updateExercise.mutate({
                              pdeId: pde.id,
                              body: { target_sets: Number(e.target.value) },
                            })
                          }
                          className="h-8 w-16"
                        />
                        <span className="text-text-tertiary text-xs">
                          {pde.target_reps_low ?? "-"}
                          {pde.target_reps_high && pde.target_reps_high !== pde.target_reps_low
                            ? `-${pde.target_reps_high}`
                            : ""}{" "}
                          reps
                        </span>
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
                    </div>
                  );
                })
              )}
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setPickerOpenForDay(day.id)}
              >
                + Add exercise
              </Button>
            </CardContent>
          </Card>
        ) : null}
      </div>

      <aside className="w-full lg:w-72">
        <VolumeSummary program={p} exercises={exMeta.data ?? new Map()} />
      </aside>

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
                className={`inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold uppercase tracking-[0.1em] ${
                  weekday === idx
                    ? "border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)] text-accent"
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
