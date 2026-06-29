"use client";

import { keepPreviousData, useInfiniteQuery } from "@tanstack/react-query";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Plus } from "lucide-react";
import { memo, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";

import { CreateExerciseSheet } from "@/components/exercise/create-exercise-sheet";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/motion-sheet";
import { labelize, MOVEMENT_PATTERNS, type MovementPattern } from "@/lib/api/exercises";
import { searchExercises } from "@/lib/api/workouts";
import { cn } from "@/lib/cn";
import type { Exercise } from "@/lib/workouts/types";

interface ExercisePickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPick: (exercise: Exercise) => void;
  /** Pre-select this movement_pattern filter when the picker opens (user can change it). */
  initialMovementPattern?: MovementPattern;
}

type Tab = "all" | "mine";

export function ExercisePicker({
  open,
  onOpenChange,
  onPick,
  initialMovementPattern,
}: ExercisePickerProps) {
  const [tab, setTab] = useState<Tab>("all");
  const [query, setQuery] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [movementPattern, setMovementPattern] = useState<MovementPattern | "all">("all");
  const deferredQuery = useDeferredValue(query);

  // Seed the movement_pattern filter from the prop each time the picker opens.
  useEffect(() => {
    if (open) {
      setMovementPattern(initialMovementPattern ?? "all");
    }
  }, [open, initialMovementPattern]);

  const activePattern = movementPattern === "all" ? undefined : movementPattern;

  const list = useInfiniteQuery({
    queryKey: ["exercises", tab, deferredQuery, movementPattern],
    queryFn: ({ pageParam }) =>
      searchExercises(deferredQuery || undefined, {
        mine_only: tab === "mine",
        limit: 100,
        cursor: pageParam,
        movement_pattern: activePattern,
      }),
    initialPageParam: undefined as string | undefined,
    // The API only paginates when browsing (no search); a `q` query orders by
    // similarity and returns a null cursor, so search collapses to one page.
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    enabled: open,
    staleTime: 30_000,
    // Keep the previous results on screen while the next query loads so typing
    // (or switching tabs) doesn't flash "Loading…"/empty between keystrokes.
    placeholderData: keepPreviousData,
  });

  const pick = (ex: Exercise) => {
    onPick(ex);
    onOpenChange(false);
  };

  const items = useMemo(() => list.data?.pages.flatMap((p) => p.items) ?? [], [list.data]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange} title="Add exercise">
      <div className="flex flex-col gap-3">
        <div className="border-border flex gap-[18px] border-b">
          {(["all", "mine"] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setTab(value)}
              className={cn(
                "-mb-px border-b-[1.5px] border-transparent pb-[7px] text-xs font-semibold tracking-[0.08em] uppercase",
                "transition-colors duration-150 ease-out",
                tab === value ? "text-text border-text" : "text-text-secondary hover:text-text",
              )}
            >
              {value === "all" ? "All" : "Mine"}
            </button>
          ))}
        </div>
        <Input
          autoFocus
          placeholder="Search exercises..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        {/* Movement pattern filter */}
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          <FilterChip active={movementPattern === "all"} onClick={() => setMovementPattern("all")}>
            All
          </FilterChip>
          {MOVEMENT_PATTERNS.map((pattern) => (
            <FilterChip
              key={pattern}
              active={movementPattern === pattern}
              onClick={() => setMovementPattern(pattern)}
            >
              {labelize(pattern)}
            </FilterChip>
          ))}
        </div>

        {list.isLoading ? (
          <p className="text-text-secondary text-sm">Loading...</p>
        ) : list.isError ? (
          <p className="text-destructive text-sm">Could not load exercises.</p>
        ) : items.length === 0 ? (
          <p className="text-text-secondary text-sm">No matches.</p>
        ) : (
          <ExerciseResults
            items={items}
            onPick={pick}
            hasNextPage={list.hasNextPage}
            isFetchingNextPage={list.isFetchingNextPage}
            onEndReached={list.fetchNextPage}
          />
        )}

        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="border-border text-text-secondary hover:border-border-strong hover:text-text flex items-center justify-center gap-1.5 rounded-[var(--radius-button)] border border-dashed py-2.5 text-sm font-medium transition-colors"
        >
          <Plus className="h-4 w-4" aria-hidden />
          New custom exercise
        </button>
      </div>

      <CreateExerciseSheet
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(ex) => {
          // Auto-add the freshly created exercise to the current workout.
          onPick(ex as Exercise);
          onOpenChange(false);
        }}
      />
    </Sheet>
  );
}

function FilterChip({
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

/**
 * Windowed exercise list: only the rows in (and just around) the viewport mount,
 * so a long list scrolls smoothly. Mirrors the food picker's virtualized results
 * (`ingredient-picker.tsx`).
 */
export function ExerciseResults({
  items,
  onPick,
  onEndReached,
  hasNextPage = false,
  isFetchingNextPage = false,
}: {
  items: Exercise[];
  onPick: (exercise: Exercise) => void;
  /** Called when the user scrolls near the end so the next page can load. */
  onEndReached?: () => void;
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
}) {
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 64,
    overscan: 6,
  });

  // Load the next page once the last few windowed rows come into view.
  const virtualItems = virtualizer.getVirtualItems();
  useEffect(() => {
    if (!onEndReached || !hasNextPage || isFetchingNextPage) return;
    const last = virtualItems[virtualItems.length - 1];
    if (last && last.index >= items.length - 8) onEndReached();
  }, [virtualItems, items.length, hasNextPage, isFetchingNextPage, onEndReached]);

  return (
    <div ref={parentRef} className="max-h-[60vh] overflow-y-auto">
      <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
        {virtualItems.map((virtualRow) => {
          const ex = items[virtualRow.index];
          if (!ex) return null;
          return (
            <div
              key={ex.id}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              <ExerciseRow exercise={ex} onPick={onPick} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const ExerciseRow = memo(function ExerciseRow({
  exercise,
  onPick,
}: {
  exercise: Exercise;
  onPick: (exercise: Exercise) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onPick(exercise)}
      className="hover:bg-surface border-border flex w-full items-center justify-between gap-3 border-b px-2 py-3 text-left transition-colors duration-150 ease-out last:border-b-0"
    >
      <div className="flex min-w-0 flex-col gap-1">
        <span className="text-text truncate text-sm font-medium">{exercise.name}</span>
        <span className="text-text-tertiary truncate text-xs">
          {labelize(exercise.primary_muscle)} · {labelize(exercise.equipment)}
        </span>
      </div>
      <span className="text-text-tertiary shrink-0 text-[10px] font-semibold tracking-[0.1em] whitespace-nowrap uppercase">
        {labelize(exercise.tracking_type)}
      </span>
    </button>
  );
});
