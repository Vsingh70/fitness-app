"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useToastStore } from "@/components/ui/toast";
import type { BodyMetric } from "@/lib/api/body-metrics";
import { useDeleteBodyMetric } from "@/lib/hooks/body-metrics";
import type { components } from "@/lib/api/types";
import {
  formatShortDate,
  formatWeight,
  relativeDate,
  round1,
  toNum,
} from "@/lib/utils/format-weight";

type UnitSystem = components["schemas"]["UnitSystem"];

interface Props {
  items: BodyMetric[] | undefined;
  isLoading: boolean;
  isError: boolean;
  unit: UnitSystem | undefined;
}

export function WeightHistoryList({ items, isLoading, isError, unit }: Props) {
  const del = useDeleteBodyMetric();
  const pushToast = useToastStore((s) => s.push);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  const onDelete = (id: string) => {
    del.mutate(id, {
      onError: () => pushToast({ kind: "error", message: "Couldn't delete. Try again." }),
      onSettled: () => setConfirmingId(null),
    });
  };

  if (isLoading) {
    return <p className="text-text-secondary text-sm">Loading…</p>;
  }
  if (isError) {
    return <p className="text-destructive text-sm">Couldn&apos;t load history.</p>;
  }
  if (!items || items.length === 0) {
    return (
      <p className="text-text-secondary text-sm">
        No entries yet. Log your weight to start tracking.
      </p>
    );
  }

  return (
    <ul className="flex flex-col">
      {items.map((r) => {
        const fat = toNum(r.body_fat_pct);
        return (
          <li key={r.id}>
            <div className="border-border flex items-center justify-between gap-3 border-b py-3 last:border-b-0">
              <div className="flex min-w-0 flex-col">
                <span className="text-text text-sm font-medium">
                  {formatShortDate(r.recorded_at)}
                </span>
                <span className="text-text-tertiary text-xs">{relativeDate(r.recorded_at)}</span>
              </div>
              <div className="text-text ml-auto text-sm tabular-nums">
                {formatWeight(r.weight_kg, unit)}
                {fat !== null ? (
                  <span className="text-text-tertiary"> · {round1(fat)}%</span>
                ) : null}
              </div>
              {confirmingId === r.id ? (
                <div className="flex items-center gap-2">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => onDelete(r.id)}
                    disabled={del.isPending}
                  >
                    Delete
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setConfirmingId(null)}>
                    Cancel
                  </Button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmingId(r.id)}
                  aria-label="Delete entry"
                  className="text-text-tertiary hover:text-destructive transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
