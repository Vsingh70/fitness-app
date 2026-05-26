"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCreateProgram } from "@/lib/hooks/programs";
import type { ProgramGoal } from "@/lib/programs/types";

const GOALS: ProgramGoal[] = ["hypertrophy", "strength", "powerbuilding", "general", "custom"];

export default function NewProgramPage() {
  const router = useRouter();
  const create = useCreateProgram();
  const [name, setName] = useState("");
  const [goal, setGoal] = useState<ProgramGoal>("hypertrophy");
  const [weeks, setWeeks] = useState(6);
  const [daysPerWeek, setDaysPerWeek] = useState(4);

  const submit = () => {
    if (!name.trim()) return;
    create.mutate(
      { name: name.trim(), goal, weeks, days_per_week: daysPerWeek },
      { onSuccess: (program) => router.push(`/programs/${program.id}`) },
    );
  };

  return (
    <div className="mx-auto flex max-w-md flex-col gap-4">
      <h1 className="text-3xl font-semibold tracking-tight">New program</h1>
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Setup</h2>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
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
              className="bg-surface text-text border-border h-10 rounded-[var(--radius-button)] border px-3"
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
