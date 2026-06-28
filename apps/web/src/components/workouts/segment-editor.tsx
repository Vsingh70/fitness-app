"use client";

import { Plus, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import {
  SET_TYPE_LABEL,
  STRUCTURED_SET_TYPES,
  sumSegmentReps,
  type SetCreate,
  type SetSegmentCreate,
  type StructuredSetType,
} from "@/lib/workouts/types";

interface SegmentDraft {
  reps: string;
  weight_kg: string;
  rest_seconds: string;
}

interface SegmentEditorProps {
  /** Whether a previous weight exists to pre-fill each bout. */
  defaultWeightKg?: number | null;
  /** Commit the structured set: builds `segments` + chosen `set_type`. */
  onSubmit: (payload: SetCreate) => void | Promise<void>;
  onCancel?: () => void;
}

function emptyBout(weight: number | null): SegmentDraft {
  return {
    reps: "",
    weight_kg: weight != null && weight > 0 ? String(weight) : "",
    rest_seconds: "20",
  };
}

/**
 * Editor for an intra-set effort made of `mini_set` sub-bouts (06 §3a):
 * rest-pause / cluster / myo-rep. Each bout records reps (and optional weight),
 * and a short rest between bouts. Total reps = sum of bout reps — shown live.
 */
export function SegmentEditor({ defaultWeightKg = null, onSubmit, onCancel }: SegmentEditorProps) {
  const [setType, setSetType] = useState<StructuredSetType>("myo_rep");
  const [bouts, setBouts] = useState<SegmentDraft[]>(() => [
    emptyBout(defaultWeightKg),
    emptyBout(defaultWeightKg),
  ]);
  const [error, setError] = useState<string | null>(null);

  const totalReps = sumSegmentReps(
    bouts.map((b) => ({ kind: "mini_set" as const, reps: Number.parseInt(b.reps, 10) || 0 })),
  );

  const setBout = (idx: number, patch: Partial<SegmentDraft>) => {
    setBouts((list) => list.map((b, i) => (i === idx ? { ...b, ...patch } : b)));
    setError(null);
  };

  const addBout = () => setBouts((list) => [...list, emptyBout(defaultWeightKg)]);

  const removeBout = (idx: number) =>
    setBouts((list) => (list.length <= 1 ? list : list.filter((_, i) => i !== idx)));

  const commit = async () => {
    const segments: SetSegmentCreate[] = [];
    bouts.forEach((b, i) => {
      const reps = Number.parseInt(b.reps, 10);
      if (!Number.isFinite(reps) || reps <= 0) return;
      const seg: SetSegmentCreate = { kind: "mini_set", segment_index: segments.length, reps };
      if (/^[\d.]+$/.test(b.weight_kg)) seg.weight_kg = b.weight_kg;
      if (i < bouts.length - 1 && /^\d+$/.test(b.rest_seconds)) {
        seg.rest_seconds = Number.parseInt(b.rest_seconds, 10);
      }
      segments.push(seg);
    });
    if (segments.length < 2) {
      setError("A rest-pause/cluster set needs at least two bouts with reps.");
      return;
    }
    setError(null);
    const firstWeight = segments.find((s) => s.weight_kg != null)?.weight_kg;
    const payload: SetCreate = {
      set_type: setType,
      reps: totalReps,
      segments,
      ...(firstWeight != null ? { weight_kg: firstWeight } : {}),
    };
    await onSubmit(payload);
  };

  return (
    <div
      data-testid="segment-editor"
      className="border-border bg-surface flex flex-col gap-3 rounded-[var(--radius-card)] border p-3"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.12em] uppercase">
          Structure
        </span>
        {STRUCTURED_SET_TYPES.map((t) => (
          <button
            key={t}
            type="button"
            aria-pressed={setType === t}
            onClick={() => setSetType(t)}
            className={cn(
              "inline-flex h-[26px] items-center rounded-[var(--radius-pill)] border px-3 text-[11px] font-semibold tracking-[0.06em] uppercase transition-colors duration-150",
              setType === t
                ? "bg-accent text-accent-foreground border-transparent"
                : "border-border text-text-secondary hover:text-text",
            )}
          >
            {SET_TYPE_LABEL[t]}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="text-text-tertiary grid grid-cols-[2.5rem_1fr_1fr_1fr_auto] items-center gap-2 px-1 text-[10px] font-semibold tracking-[0.1em] uppercase">
          <span>Bout</span>
          <span>Reps</span>
          <span>kg</span>
          <span>Rest s</span>
          <span />
        </div>
        {bouts.map((b, idx) => (
          <div key={idx} className="grid grid-cols-[2.5rem_1fr_1fr_1fr_auto] items-center gap-2">
            <span className="text-text-secondary font-serif text-[15px] tabular-nums">
              {idx + 1}
            </span>
            <Input
              inputMode="numeric"
              aria-label={`Reps for bout ${idx + 1}`}
              value={b.reps}
              onChange={(e) => setBout(idx, { reps: e.target.value })}
              placeholder="reps"
              className="h-9 text-right font-serif font-medium tabular-nums"
            />
            <Input
              inputMode="decimal"
              aria-label={`Weight for bout ${idx + 1}`}
              value={b.weight_kg}
              onChange={(e) => setBout(idx, { weight_kg: e.target.value })}
              placeholder="kg"
              className="h-9 text-right font-serif font-medium tabular-nums"
            />
            {idx < bouts.length - 1 ? (
              <Input
                inputMode="numeric"
                aria-label={`Rest after bout ${idx + 1}`}
                value={b.rest_seconds}
                onChange={(e) => setBout(idx, { rest_seconds: e.target.value })}
                placeholder="rest"
                className="h-9 text-right font-serif font-medium tabular-nums"
              />
            ) : (
              <span className="text-text-tertiary text-center text-xs">—</span>
            )}
            <Button
              type="button"
              size="sm"
              variant="ghost"
              aria-label={`Remove bout ${idx + 1}`}
              disabled={bouts.length <= 1}
              onClick={() => removeBout(idx)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button type="button" size="sm" variant="ghost" onClick={addBout}>
          <Plus className="mr-1 h-4 w-4" /> Bout (rest-pause)
        </Button>
        <span
          className="text-text-secondary text-xs"
          data-testid="segment-total"
          aria-live="polite"
        >
          Total{" "}
          <span className="text-text font-serif text-[15px] font-medium tabular-nums">
            {totalReps}
          </span>{" "}
          reps
        </span>
      </div>

      {error ? (
        <p role="alert" className="text-destructive text-xs">
          {error}
        </p>
      ) : null}

      <div className="flex items-center gap-2">
        <Button type="button" size="sm" onClick={() => void commit()}>
          Save {SET_TYPE_LABEL[setType].toLowerCase()}
        </Button>
        {onCancel ? (
          <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
      </div>
    </div>
  );
}
