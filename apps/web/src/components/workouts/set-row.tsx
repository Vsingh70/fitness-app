"use client";

import { X } from "lucide-react";
import { memo, useState, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import { displayToKg, kgToDisplay, weightUnitLabel } from "@/lib/utils/format-weight";
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
  isCurrent?: boolean;
  isCompleted?: boolean;
  /** User's unit system; drives weight display (kg vs lb) and write-path conversion. */
  unit?: "metric" | "imperial";
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

export const SetRow = memo(function SetRow({
  trackingType,
  previousSummary,
  setIndex,
  initial = {},
  isPending = false,
  isPr = false,
  isCurrent = false,
  isCompleted = false,
  unit,
  onSubmit,
  onDelete,
}: SetRowProps) {
  const columns = TRACKING_COLUMNS[trackingType];
  // Convert weight_kg from server kg to display units for the initial draft state.
  const [draft, setDraft] = useState<Draft>(() => {
    if (!initial.weight_kg) return initial;
    const displayVal = kgToDisplay(initial.weight_kg, unit);
    if (displayVal === null) return initial;
    return { ...initial, weight_kg: String(displayVal) };
  });
  const [error, setError] = useState<string | null>(null);

  const setField = (field: keyof SetCreate, value: string) => {
    setDraft((d) => ({ ...d, [field]: value }));
    setError(null);
  };

  const commit = async () => {
    const payload: Partial<Record<keyof SetCreate, unknown>> = {};
    for (const c of columns) {
      const parsed = parseValue(c, draft[c] ?? "");
      if (parsed !== undefined) {
        if (c === "weight_kg") {
          // Convert display-unit value back to kg before sending to the API.
          payload[c] = String(displayToKg(Number(parsed as string), unit));
        } else {
          payload[c] = parsed;
        }
      }
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
        isCurrent && !isCompleted ? "bg-accent-soft" : "",
        isCompleted ? "bg-success-soft" : "",
        isPr ? "bg-pr-soft" : "",
        isPending ? "opacity-60" : "",
      )}
      style={{
        gridTemplateColumns: `2rem 6rem repeat(${columns.length}, minmax(0, 1fr)) auto`,
      }}
    >
      <span
        className={cn(
          "font-serif text-[15px] tabular-nums",
          isCompleted ? "text-success" : "text-text-secondary",
        )}
      >
        {setIndex + 1}
      </span>
      <span className="text-text-tertiary truncate text-xs">{previousSummary ?? "-"}</span>
      {columns.map((c) => {
        const fieldLabel = c === "weight_kg" ? weightUnitLabel(unit) : SET_FIELD_LABEL[c];
        return (
          <Input
            key={c}
            inputMode={c === "reps" || c === "duration_seconds" ? "numeric" : "decimal"}
            aria-label={`${fieldLabel} for set ${setIndex + 1}`}
            value={draft[c] ?? ""}
            onChange={(e) => setField(c, e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={fieldLabel}
            className="h-9 text-right font-serif font-medium tabular-nums"
          />
        );
      })}
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
            <X className="h-4 w-4" />
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
});
