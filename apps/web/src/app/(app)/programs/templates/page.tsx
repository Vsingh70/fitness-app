"use client";

import Link from "next/link";
import { useState } from "react";

import { UnderlineTabs } from "@/components/ui/tabs";
import { useTemplates } from "@/lib/hooks/programs";
import type { ProgramTemplateSummary } from "@/lib/programs/types";

// Match the design's filter labels (programs/screens.jsx · WebTemplates). The
// values map to real ProgramGoal strings where they exist; "endurance" has no
// enum equivalent yet, so that chip simply shows an empty state.
const FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "All" },
  { value: "hypertrophy", label: "Hypertrophy" },
  { value: "strength", label: "Strength" },
  { value: "endurance", label: "Endurance" },
  { value: "general", label: "General" },
];

export default function TemplatesBrowsePage() {
  const list = useTemplates();
  const [goal, setGoal] = useState<string>("all");

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
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

function TemplateGrid({ items, goal }: { items: ProgramTemplateSummary[]; goal: string }) {
  const filtered = items.filter((t) => goal === "all" || t.goal === goal);
  if (filtered.length === 0) {
    return <p className="text-text-tertiary py-4 text-sm">No templates for this goal.</p>;
  }
  return (
    <div className="grid grid-cols-1 gap-x-7 sm:grid-cols-2">
      {filtered.map((t) => (
        <Link
          key={t.id}
          href={`/programs/templates/${t.slug}`}
          className="border-border hover:border-text/40 group block border-b py-[18px] transition-colors"
        >
          <div className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] capitalize">
            <span className="uppercase">{t.goal.replace(/_/g, " ")}</span>
          </div>
          <div className="group-hover:text-accent mt-1 mb-1.5 font-serif text-[22px] tracking-[-0.01em] transition-colors">
            {t.name}
          </div>
          {t.description ? (
            <p className="text-text-secondary min-h-[38px] text-[13px] leading-[1.5]">
              {t.description}
            </p>
          ) : null}
          <div className="text-text-tertiary mt-2.5 flex gap-4 text-[11px]">
            <span>
              <b className="text-text-secondary font-serif font-medium tabular-nums">{t.weeks}</b>{" "}
              weeks
            </span>
            <span>
              <b className="text-text-secondary font-serif font-medium tabular-nums">
                {t.days_per_week}
              </b>
              /week
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
