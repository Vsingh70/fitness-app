"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { useToastStore } from "@/components/ui/toast";
import type { BodyMetricCreate } from "@/lib/api/body-metrics";
import { useLogBodyMetric } from "@/lib/hooks/body-metrics";
import { useMe } from "@/lib/hooks/me";
import { displayToKg, weightUnitLabel } from "@/lib/utils/format-weight";

interface Props {
  open: boolean;
  onClose: () => void;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
        {label}
      </span>
      {children}
    </label>
  );
}

function todayLocal(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function LogWeightSheet({ open, onClose }: Props) {
  const me = useMe();
  const unit = me.data?.unit_system;
  const mutation = useLogBodyMetric();
  const pushToast = useToastStore((s) => s.push);

  const [weight, setWeight] = useState("");
  const [bodyFat, setBodyFat] = useState("");
  const [date, setDate] = useState(todayLocal);

  // Reset form whenever the sheet opens so stale values don't persist across dismissals.
  useEffect(() => {
    if (open) {
      setWeight("");
      setBodyFat("");
      setDate(todayLocal());
    }
  }, [open]);

  const weightNum = Number(weight);
  const validWeight = weight.trim() !== "" && Number.isFinite(weightNum) && weightNum > 0;

  const submit = async () => {
    if (!validWeight || mutation.isPending) return;
    const recorded_at = new Date(`${date}T12:00:00`).toISOString(); // local NOON -> avoids UTC date-shift
    const kg = displayToKg(weightNum, unit); // unrounded
    const body: BodyMetricCreate = {
      recorded_at,
      weight_kg: kg.toFixed(2),
      body_fat_pct:
        bodyFat.trim() !== "" && Number.isFinite(Number(bodyFat))
          ? Number(bodyFat).toFixed(1)
          : null,
    };
    try {
      await mutation.mutateAsync(body);
      pushToast({ kind: "success", message: "Weight logged" });
      setWeight("");
      setBodyFat("");
      setDate(todayLocal());
      onClose();
    } catch {
      pushToast({ kind: "error", message: "Couldn't save. Try again." });
    }
  };

  return (
    <Sheet open={open} onOpenChange={(v) => (v ? null : onClose())} title="Log weight">
      <div className="flex flex-col gap-4">
        <Field label={`Weight (${weightUnitLabel(unit)})`}>
          <Input
            type="number"
            inputMode="decimal"
            step="0.1"
            autoFocus
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
          />
        </Field>

        <Field label="Body fat % (optional)">
          <Input
            type="number"
            inputMode="decimal"
            step="0.1"
            value={bodyFat}
            onChange={(e) => setBodyFat(e.target.value)}
          />
        </Field>

        <Field label="Date">
          <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </Field>

        <div className="mt-1 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit} disabled={!validWeight || mutation.isPending}>
            {mutation.isPending ? "Saving…" : "Log weight"}
          </Button>
        </div>
      </div>
    </Sheet>
  );
}
