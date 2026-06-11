"use client";

import Link from "next/link";
import { useState } from "react";

import { UnderlineTabs } from "@/components/ui/tabs";
import { useTemplates } from "@/lib/hooks/programs";
import type { ProgramGoal, ProgramTemplateSummary } from "@/lib/programs/types";

type Filter = ProgramGoal | "all";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "hypertrophy", label: "Hypertrophy" },
  { value: "strength", label: "Strength" },
  { value: "powerbuilding", label: "Powerbuilding" },
  { value: "fat_loss", label: "Fat loss" },
  { value: "general", label: "General" },
];

export default function TemplatesBrowsePage() {
  const list = useTemplates();
  const [goal, setGoal] = useState<Filter>("all");

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-7">
      <header>
        <p className="text-text-tertiary text-xs">
          <Link href="/programs" className="hover:text-text">
            Programs
          </Link>{" "}
          ›
        </p>
        <h1 className="mt-1 font-serif text-[32px] leading-tight font-medium tracking-tight">
          Browse templates
        </h1>
        <p className="text-text-secondary mt-1.5 text-sm">
          Pick a proven program, copy it, and start this week.
        </p>
      </header>

      <UnderlineTabs
        tabs={FILTERS}
        value={goal}
        onChange={setGoal}
        ariaLabel="Filter templates by goal"
      />

      {list.isLoading ? (
        <p className="text-text-secondary">Loading…</p>
      ) : list.isError ? (
        <p className="text-destructive">Could not load templates.</p>
      ) : (
        <TemplateGrid items={list.data?.items ?? []} goal={goal} />
      )}
    </div>
  );
}

function TemplateGrid({ items, goal }: { items: ProgramTemplateSummary[]; goal: Filter }) {
  const filtered = items.filter((t) => goal === "all" || t.goal === goal);
  if (filtered.length === 0) {
    return <p className="text-text-tertiary text-sm">No templates for this goal.</p>;
  }
  return (
    <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
      {filtered.map((t) => (
        <Link
          key={t.id}
          href={`/programs/templates/${t.slug}`}
          className="border-border bg-surface-elevated hover:border-text flex h-full flex-col gap-2 rounded-[var(--radius-card)] border p-[18px] transition-colors duration-150 ease-out"
        >
          <div className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
            {t.goal}
          </div>
          <div className="font-serif text-[18px] font-medium tracking-tight">{t.name}</div>
          {t.description ? (
            <p className="text-text-secondary min-h-[38px] text-[13px] leading-relaxed">
              {t.description}
            </p>
          ) : null}
          <div className="border-border text-text-tertiary mt-auto flex gap-3 border-t pt-2.5 text-[11px]">
            <span>
              <b className="text-text-secondary font-semibold tabular-nums">{t.weeks}</b> weeks
            </span>
            <span>
              <b className="text-text-secondary font-semibold tabular-nums">{t.days_per_week}</b>
              ×/week
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
