"use client";

import { AlertTriangle, Check } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { computeVolume, type VolumeEntry } from "@/lib/programs/volume";
import type { components } from "@/lib/api/types";

type Program = components["schemas"]["ProgramResponse"];
type Exercise = components["schemas"]["ExerciseResponse"];

interface VolumeSummaryProps {
  program: Program;
  exercises: Map<string, Exercise>;
}

export function VolumeSummary({ program, exercises }: VolumeSummaryProps) {
  const entries = computeVolume(program, exercises);
  return (
    <Card>
      <CardHeader>
        <h2 className="text-sm font-semibold tracking-wide uppercase">Weekly volume</h2>
        <p className="text-text-tertiary text-xs">
          Primary muscle 1.0 / secondary 0.5 per target set. Warns outside 8 - 22 sets.
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-1">
        {entries.length === 0 ? (
          <p className="text-text-secondary text-sm">Add exercises to see volume.</p>
        ) : (
          entries.map((entry) => <VolumeRow key={entry.muscle} entry={entry} />)
        )}
      </CardContent>
    </Card>
  );
}

function VolumeRow({ entry }: { entry: VolumeEntry }) {
  const dotClass = {
    low: "text-warning",
    ok: "text-success",
    high: "text-warning",
  }[entry.status];
  const Icon = entry.status === "ok" ? Check : AlertTriangle;
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="flex items-center gap-2">
        <Icon className={cn("h-3 w-3", dotClass)} />
        <span className="text-text">{entry.muscle.replace(/_/g, " ")}</span>
      </span>
      <span className={cn("tabular-nums", dotClass)}>{entry.sets}</span>
    </div>
  );
}
