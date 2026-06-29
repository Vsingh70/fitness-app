"use client";

import Link from "next/link";
import { useState } from "react";
import { Plus, Search } from "lucide-react";

import { CreateExerciseSheet } from "@/components/exercise/create-exercise-sheet";
import { Button } from "@/components/ui/button";
import { UnderlineTabs } from "@/components/ui/tabs";
import {
  EQUIPMENT,
  MOVEMENT_PATTERNS,
  MUSCLES,
  labelize,
  type Equipment,
  type Exercise,
  type MovementPattern,
  type Muscle,
} from "@/lib/api/exercises";
import { useInfiniteExercises } from "@/lib/hooks/exercises";

type Scope = "all" | "mine";

interface ExerciseLibraryProps {
  /**
   * Render the standalone page header (kicker + "Exercises" title + New button).
   * The `/exercises` route wants it; inside the Workouts hub the section already
   * carries its own heading, so it's suppressed there (the New action moves to a
   * compact button rendered alongside the toolbar instead).
   */
  showHeader?: boolean;
}

/**
 * The exercise library body — search + scope tabs + muscle/equipment filters +
 * a results grid whose cards link to `/exercises/{id}`. Extracted so both the
 * `/exercises` route and the Workouts hub's Library section render the same
 * surface (folding the formerly desktop-only page in for mobile too).
 */
export function ExerciseLibrary({ showHeader = true }: ExerciseLibraryProps) {
  const [scope, setScope] = useState<Scope>("all");
  const [query, setQuery] = useState("");
  const [muscle, setMuscle] = useState<Muscle | "all">("all");
  const [equipment, setEquipment] = useState<Equipment | "all">("all");
  const [movementPattern, setMovementPattern] = useState<MovementPattern | "all">("all");
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading, isError, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useInfiniteExercises({
      q: query.trim() || undefined,
      muscle: muscle === "all" ? undefined : muscle,
      equipment: equipment === "all" ? undefined : equipment,
      movement_pattern: movementPattern === "all" ? undefined : movementPattern,
      mine_only: scope === "mine",
      limit: 100,
    });

  const items = data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <div>
      {showHeader ? (
        <header className="mb-5 flex items-end justify-between gap-3">
          <div>
            <p className="text-text-tertiary text-[11px] font-semibold tracking-[0.12em] uppercase">
              Library
            </p>
            <h1 className="font-serif text-[28px] font-medium tracking-tight">Exercises</h1>
          </div>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" aria-hidden />
            New exercise
          </Button>
        </header>
      ) : null}

      <div className="flex items-center justify-between gap-3">
        <UnderlineTabs
          tabs={[
            { value: "all", label: "All" },
            { value: "mine", label: "My exercises" },
          ]}
          value={scope}
          onChange={(v) => setScope(v as Scope)}
          ariaLabel="Exercise scope"
          className="flex-1"
        />
        {showHeader ? null : (
          <Button size="sm" variant="secondary" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" aria-hidden />
            New
          </Button>
        )}
      </div>

      {/* Search */}
      <div className="bg-surface border-border mt-4 flex items-center gap-2 rounded-[10px] border px-3 py-2">
        <Search className="text-text-tertiary h-4 w-4 shrink-0" aria-hidden />
        <input
          type="search"
          placeholder="Search exercises…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="text-text placeholder:text-text-tertiary w-full bg-transparent text-sm outline-none"
        />
      </div>

      {/* Filters */}
      <div className="mt-3 flex flex-col gap-2">
        <FilterRow
          label="Muscle"
          options={MUSCLES}
          value={muscle}
          onChange={(v) => setMuscle(v as Muscle | "all")}
        />
        <FilterRow
          label="Equipment"
          options={EQUIPMENT}
          value={equipment}
          onChange={(v) => setEquipment(v as Equipment | "all")}
        />
        <FilterRow
          label="Pattern"
          options={MOVEMENT_PATTERNS}
          value={movementPattern}
          onChange={(v) => setMovementPattern(v as MovementPattern | "all")}
        />
      </div>

      {/* Results */}
      <div className="mt-5">
        {isLoading ? (
          <p className="text-text-secondary py-8 text-center text-sm">Loading…</p>
        ) : isError ? (
          <p className="text-destructive py-8 text-center text-sm">Couldn&apos;t load exercises.</p>
        ) : items.length === 0 ? (
          <div className="py-10 text-center">
            <p className="text-text-secondary text-sm">
              {scope === "mine" ? "No custom exercises yet." : "No exercises match those filters."}
            </p>
            {scope === "mine" ? (
              <Button
                size="sm"
                variant="secondary"
                className="mt-3"
                onClick={() => setCreateOpen(true)}
              >
                Create your first
              </Button>
            ) : null}
          </div>
        ) : (
          <>
            <p className="text-text-tertiary mb-2 text-[11px] font-semibold tracking-[0.08em] uppercase">
              {items.length}
              {hasNextPage ? "+" : ""} exercise{items.length === 1 ? "" : "s"}
            </p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((ex) => (
                <ExerciseCard key={ex.id} exercise={ex} />
              ))}
            </div>
            {hasNextPage ? (
              <div className="mt-4 flex justify-center">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => fetchNextPage()}
                  disabled={isFetchingNextPage}
                >
                  {isFetchingNextPage ? "Loading…" : "Load more"}
                </Button>
              </div>
            ) : null}
          </>
        )}
      </div>

      <CreateExerciseSheet open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}

function FilterRow({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-text-tertiary w-[72px] shrink-0 text-[11px] font-semibold tracking-[0.08em] uppercase">
        {label}
      </span>
      <div className="flex flex-1 gap-1.5 overflow-x-auto pb-1">
        <Chip active={value === "all"} onClick={() => onChange("all")}>
          All
        </Chip>
        {options.map((opt) => (
          <Chip key={opt} active={value === opt} onClick={() => onChange(opt)}>
            {labelize(opt)}
          </Chip>
        ))}
      </div>
    </div>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "shrink-0 rounded-[var(--radius-pill)] border px-2.5 py-1 text-xs font-medium transition-colors " +
        (active
          ? "border-accent bg-accent-soft text-accent"
          : "border-border text-text-secondary hover:border-border-strong")
      }
    >
      {children}
    </button>
  );
}

function ExerciseCard({ exercise }: { exercise: Exercise }) {
  return (
    <Link
      href={`/exercises/${exercise.id}`}
      className="border-border bg-surface-elevated hover:border-border-strong flex flex-col gap-1 rounded-[var(--radius-card)] border p-3 transition-colors"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-text text-sm leading-snug font-semibold">{exercise.name}</span>
        {exercise.owner_id ? (
          <span className="border-accent text-accent shrink-0 rounded-[var(--radius-pill)] border px-1.5 py-0.5 text-[9px] font-semibold tracking-[0.06em] uppercase">
            Custom
          </span>
        ) : null}
      </div>
      <span className="text-text-secondary text-xs">
        {labelize(exercise.primary_muscle)} · {labelize(exercise.equipment)}
      </span>
    </Link>
  );
}
