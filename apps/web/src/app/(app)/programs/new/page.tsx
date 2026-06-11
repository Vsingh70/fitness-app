"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PeriodizationControl } from "@/components/programs/periodization-control";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCreateProgram } from "@/lib/hooks/programs";
import type { PeriodizationMode, ProgramGoal } from "@/lib/programs/types";

const GOALS: ProgramGoal[] = ["hypertrophy", "strength", "powerbuilding", "general", "custom"];

export default function NewProgramPage() {
  const router = useRouter();
  const create = useCreateProgram();
  const [name, setName] = useState("");
  const [goal, setGoal] = useState<ProgramGoal>("hypertrophy");
  const [weeks, setWeeks] = useState(6);
  const [daysPerWeek, setDaysPerWeek] = useState(4);
  const [mode, setMode] = useState<PeriodizationMode>("block");
  const [autoDeloadOnStall, setAutoDeloadOnStall] = useState(true);

  const submit = () => {
    if (!name.trim()) return;
    create.mutate(
      {
        name: name.trim(),
        goal,
        weeks,
        days_per_week: daysPerWeek,
        periodization_mode: mode,
        auto_deload_on_stall: autoDeloadOnStall,
        // Default scale; the builder's global "Intensity tracking" control can
        // switch it (or turn it off) after creation.
        intensity_mode: "rpe",
      },
      { onSuccess: (program) => router.push(`/programs/${program.id}`) },
    );
  };

  return (
    <div className="mx-auto flex max-w-md flex-col gap-4">
      <header>
        <p className="text-text-tertiary text-xs">Programs ›</p>
        <h1 className="font-serif text-[32px] leading-tight font-medium tracking-tight">
          New program
        </h1>
        <p className="text-text-secondary mt-1.5 text-sm">Start from scratch, then add days.</p>
      </header>
      <Card>
        <CardHeader>
          <span>Setup</span>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <PeriodizationControl
            mode={mode}
            onChange={setMode}
            autoDeloadOnStall={autoDeloadOnStall}
            onAutoDeloadOnStallChange={setAutoDeloadOnStall}
            disabled={create.isPending}
          />
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">Name</span>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My program"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-text-secondary">Goal</span>
            <select
              className="border-border-strong bg-surface-elevated text-text focus:border-accent focus:ring-accent-soft h-[42px] rounded-[var(--radius-button)] border px-3 text-sm capitalize focus:ring-[3px] focus:outline-none"
              value={goal}
              onChange={(e) => setGoal(e.target.value as ProgramGoal)}
            >
              {GOALS.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>
          <div className="flex gap-3">
            {mode === "block" ? (
              <label className="flex flex-1 flex-col gap-1 text-sm">
                <span className="text-text-secondary">Weeks</span>
                <Input
                  type="number"
                  min={1}
                  max={52}
                  value={weeks}
                  onChange={(e) => setWeeks(Number(e.target.value))}
                />
              </label>
            ) : null}
            <label className="flex flex-1 flex-col gap-1 text-sm">
              <span className="text-text-secondary">Days / week</span>
              <Input
                type="number"
                min={1}
                max={7}
                value={daysPerWeek}
                onChange={(e) => setDaysPerWeek(Number(e.target.value))}
              />
            </label>
          </div>
          <Button type="button" onClick={submit} disabled={create.isPending || !name.trim()}>
            {create.isPending ? "Creating..." : "Create"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
