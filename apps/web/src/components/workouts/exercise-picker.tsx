"use client";

import { useQuery } from "@tanstack/react-query";
import { useDeferredValue, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
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
        <div className="flex gap-2">
          <Button
            type="button"
            variant={tab === "all" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setTab("all")}
          >
            All
          </Button>
          <Button
            type="button"
            variant={tab === "mine" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setTab("mine")}
          >
            Mine
          </Button>
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
                className="hover:bg-surface flex items-center justify-between rounded-[var(--radius-button)] px-3 py-2 text-left"
                onClick={() => {
                  onPick(ex);
                  onOpenChange(false);
                }}
              >
                <div className="flex flex-col">
                  <span className="text-text font-medium">{ex.name}</span>
                  <span className="text-text-tertiary text-xs">
                    {ex.primary_muscle} - {ex.equipment}
                  </span>
                </div>
                <span className="text-text-tertiary text-xs">{ex.tracking_type}</span>
              </button>
            ))
          )}
        </div>
      </div>
    </Sheet>
  );
}
