"use client";

import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import type { components } from "@/lib/api/types";

type VariantRow = components["schemas"]["VariantRowResponse"];

interface Props {
  variants: VariantRow[];
}

export function VariantsList({ variants }: Props) {
  if (variants.length === 0) {
    return (
      <Card>
        <CardContent>
          <p className="text-text-secondary text-sm">
            No variants suggested yet — try logging more sets across equipment types.
          </p>
        </CardContent>
      </Card>
    );
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {variants.map(({ exercise, usage_count }) => (
        <Link
          key={exercise.id}
          href={`/exercises/${exercise.id}`}
          className="border-border bg-surface-elevated hover:bg-surface flex flex-col gap-1.5 rounded-[var(--radius-card)] border p-4 transition-colors duration-150 ease-out"
        >
          <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
            {exercise.equipment.replace(/_/g, " ")} · {exercise.primary_muscle.replace(/_/g, " ")}
          </span>
          <span className="text-text font-serif text-base font-medium tracking-tight">
            {exercise.name}
          </span>
          <span className="text-text-secondary text-[12px]">
            <b className="text-text font-serif font-medium tabular-nums">{usage_count}</b> session
            {usage_count === 1 ? "" : "s"} logged
          </span>
        </Link>
      ))}
    </div>
  );
}
