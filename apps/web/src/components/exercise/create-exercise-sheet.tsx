"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { useToastStore } from "@/components/ui/toast";
import {
  EQUIPMENT,
  MOVEMENT_PATTERNS,
  MUSCLES,
  TRACKING_TYPES,
  labelize,
  type Equipment,
  type Exercise,
  type ExerciseCreate,
  type MovementPattern,
  type Muscle,
  type TrackingType,
} from "@/lib/api/exercises";
import { useCreateExercise } from "@/lib/hooks/exercises";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Called with the newly-created exercise (e.g. to auto-select it). */
  onCreated?: (exercise: Exercise) => void;
}

const selectClass =
  "border-border-strong bg-surface-elevated text-text h-[42px] w-full rounded-[var(--radius-button)] border px-3 text-sm focus:border-accent focus:ring-accent-soft focus:ring-[3px] focus:outline-none";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-text-tertiary text-[11px] font-semibold uppercase tracking-[0.08em]">
        {label}
      </span>
      {children}
    </label>
  );
}

export function CreateExerciseSheet({ open, onClose, onCreated }: Props) {
  const create = useCreateExercise();
  const pushToast = useToastStore((s) => s.push);

  const [name, setName] = useState("");
  const [primaryMuscle, setPrimaryMuscle] = useState<Muscle>("chest");
  const [equipment, setEquipment] = useState<Equipment>("barbell");
  const [movement, setMovement] = useState<MovementPattern>("horizontal_push");
  const [tracking, setTracking] = useState<TrackingType>("weight_reps");
  const [unilateral, setUnilateral] = useState(false);
  const [notes, setNotes] = useState("");

  const reset = () => {
    setName("");
    setPrimaryMuscle("chest");
    setEquipment("barbell");
    setMovement("horizontal_push");
    setTracking("weight_reps");
    setUnilateral(false);
    setNotes("");
  };

  const submit = async () => {
    if (!name.trim()) return;
    const body: ExerciseCreate = {
      name: name.trim(),
      primary_muscle: primaryMuscle,
      secondary_muscles: [],
      equipment,
      movement_pattern: movement,
      tracking_type: tracking,
      is_unilateral: unilateral,
      notes: notes.trim() || null,
      cues: null,
    };
    try {
      const created = await create.mutateAsync(body);
      pushToast({ kind: "success", message: `Added "${created.name}"` });
      reset();
      onCreated?.(created);
      onClose();
    } catch {
      pushToast({ kind: "error", message: "Could not create exercise. Try a different name." });
    }
  };

  return (
    <Sheet open={open} onOpenChange={(v) => (v ? null : onClose())} title="New custom exercise">
      <div className="flex flex-col gap-4">
        <Field label="Name">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Cable Y-Raise"
            autoFocus
            maxLength={160}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Primary muscle">
            <select
              className={selectClass}
              value={primaryMuscle}
              onChange={(e) => setPrimaryMuscle(e.target.value as Muscle)}
            >
              {MUSCLES.map((m) => (
                <option key={m} value={m}>
                  {labelize(m)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Equipment">
            <select
              className={selectClass}
              value={equipment}
              onChange={(e) => setEquipment(e.target.value as Equipment)}
            >
              {EQUIPMENT.map((eq) => (
                <option key={eq} value={eq}>
                  {labelize(eq)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Movement pattern">
            <select
              className={selectClass}
              value={movement}
              onChange={(e) => setMovement(e.target.value as MovementPattern)}
            >
              {MOVEMENT_PATTERNS.map((mp) => (
                <option key={mp} value={mp}>
                  {labelize(mp)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Tracking">
            <select
              className={selectClass}
              value={tracking}
              onChange={(e) => setTracking(e.target.value as TrackingType)}
            >
              {TRACKING_TYPES.map((tt) => (
                <option key={tt} value={tt}>
                  {labelize(tt)}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <label className="flex items-center gap-2.5">
          <input
            type="checkbox"
            checked={unilateral}
            onChange={(e) => setUnilateral(e.target.checked)}
            className="accent-[var(--color-accent)] h-4 w-4"
          />
          <span className="text-text text-sm">Unilateral (one side at a time)</span>
        </label>

        <Field label="Notes (optional)">
          <Input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Setup, form cues, machine settings…"
          />
        </Field>

        <div className="mt-1 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={create.isPending}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit} disabled={!name.trim() || create.isPending}>
            {create.isPending ? "Adding…" : "Add exercise"}
          </Button>
        </div>
      </div>
    </Sheet>
  );
}
