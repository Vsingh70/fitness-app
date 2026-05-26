"use client";

import { useState, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import {
  SET_FIELD_LABEL,
  TRACKING_COLUMNS,
  type SetCreate,
  type TrackingType,
  validateSet,
} from "@/lib/workouts/types";

type Draft = Partial<Record<keyof SetCreate, string>>;

interface SetRowProps {
  trackingType: TrackingType;
  /** Previous-session value for this set index, shown in a muted column. */
  previousSummary?: string;
  setIndex: number;
  initial?: Draft;
  isPending?: boolean;
  isPr?: boolean;
  onSubmit: (payload: SetCreate) => void | Promise<void>;
  onDelete?: () => void;
}

function parseValue(field: keyof SetCreate, raw: string): unknown {
  if (raw === "") return undefined;
  if (field === "reps" || field === "duration_seconds" || field === "rir") {
    const n = Number.parseInt(raw, 10);
    return Number.isFinite(n) ? n : undefined;
  }
  if (field === "weight_kg" || field === "distance_meters" || field === "rpe") {
    if (!/^[\d.]+$/.test(raw)) return undefined;
    return raw;
  }
  return raw;
}

export function SetRow({
  trackingType,
  previousSummary,
  setIndex,
  initial = {},
  isPending = false,
  isPr = false,
  onSubmit,
  onDelete,
}: SetRowProps) {
  const columns = TRACKING_COLUMNS[trackingType];
  const [draft, setDraft] = useState<Draft>(initial);
  const [error, setError] = useState<string | null>(null);

  const setField = (field: keyof SetCreate, value: string) => {
    setDraft((d) => ({ ...d, [field]: value }));
    setError(null);
  };

  const commit = async () => {
    const payload: Partial<Record<keyof SetCreate, unknown>> = {};
    for (const c of columns) {
      const parsed = parseValue(c, draft[c] ?? "");
      if (parsed !== undefined) payload[c] = parsed;
    }
    const result = validateSet(payload, trackingType);
    if (!result.ok) {
      setError(result.reason);
      return;
    }
    setError(null);
    await onSubmit(payload as SetCreate);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      void commit();
    }
  };

  return (
    <div
      data-testid="set-row"
      className={cn(
        "grid items-center gap-2 rounded-[var(--radius-button)] border border-transparent px-2 py-2 text-sm",
        isPr ? "bg-pr/10" : "",
        isPending ? "opacity-60" : "",
      )}
      style={{
        gridTemplateColumns: `2rem 6rem repeat(${columns.length}, minmax(0, 1fr)) auto`,
      }}
    >
      <span className="text-text-secondary tabular-nums">{setIndex + 1}</span>
      <span className="text-text-tertiary truncate text-xs">{previousSummary ?? "-"}</span>
      {columns.map((c) => (
        <Input
          key={c}
          inputMode={c === "reps" || c === "duration_seconds" ? "numeric" : "decimal"}
          aria-label={`${SET_FIELD_LABEL[c]} for set ${setIndex + 1}`}
          value={draft[c] ?? ""}
          onChange={(e) => setField(c, e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={SET_FIELD_LABEL[c]}
          className="h-9"
        />
      ))}
      <div className="flex items-center gap-1">
        <Button type="button" size="sm" onClick={() => void commit()} disabled={isPending}>
          Save
        </Button>
        {onDelete ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={onDelete}
            aria-label="Delete set"
          >
            x
          </Button>
        ) : null}
      </div>
      {error ? (
        <p role="alert" className="text-destructive col-span-full text-xs">
          {error}
        </p>
      ) : null}
    </div>
  );
}
