"use client";

import { useQuery } from "@tanstack/react-query";
import { useDeferredValue, useState } from "react";

import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { cn } from "@/lib/cn";
import { searchExercises } from "@/lib/api/workouts";
import type { Exercise } from "@/lib/workouts/types";

interface ExercisePickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPick: (exercise: Exercise) => void;
}

type Tab = "all" | "mine";

export function ExercisePicker({ open, onOpenChange, onPick }: ExercisePickerProps) {
  const [tab, setTab] = useState<Tab>("all");
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);

  const list = useQuery({
    queryKey: ["exercises", tab, deferredQuery],
    queryFn: () =>
      searchExercises(deferredQuery || undefined, {
        mine_only: tab === "mine",
        limit: 30,
      }),
    enabled: open,
    staleTime: 30_000,
  });

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
                "pb-[7px] -mb-px border-b-[1.5px] border-transparent text-xs font-semibold uppercase tracking-[0.08em]",
                "transition-colors duration-150 ease-out",
                tab === value
                  ? "text-text border-text"
                  : "text-text-secondary hover:text-text",
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
        <div className="flex max-h-[60vh] flex-col gap-1 overflow-y-auto">
          {list.isLoading ? (
            <p className="text-text-secondary text-sm">Loading...</p>
          ) : list.isError ? (
            <p className="text-destructive text-sm">Could not load exercises.</p>
          ) : list.data && list.data.items.length === 0 ? (
            <p className="text-text-secondary text-sm">No matches.</p>
          ) : (
            list.data?.items.map((ex) => (
              <button
                key={ex.id}
                type="button"
                className="hover:bg-surface border-border flex items-center justify-between gap-3 border-b px-2 py-3 text-left transition-colors duration-150 ease-out last:border-b-0"
                onClick={() => {
                  onPick(ex);
                  onOpenChange(false);
                }}
              >
                <div className="flex flex-col gap-1">
                  <span className="text-text text-sm font-medium">{ex.name}</span>
                  <span className="text-text-tertiary text-xs">
                    {ex.primary_muscle} · {ex.equipment}
                  </span>
                </div>
                <span className="text-text-tertiary text-[10px] font-semibold uppercase tracking-[0.1em]">
                  {ex.tracking_type}
                </span>
              </button>
            ))
          )}
        </div>
      </div>
    </Sheet>
  );
}
