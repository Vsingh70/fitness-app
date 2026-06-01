"use client";

import Link from "next/link";
import { useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { useMyPrograms, useTemplates } from "@/lib/hooks/programs";
import type { ProgramGoal, ProgramTemplateSummary } from "@/lib/programs/types";

type Tab = "mine" | "templates";

const GOALS: { value: ProgramGoal | "all"; label: string }[] = [
  { value: "all", label: "All goals" },
  { value: "hypertrophy", label: "Hypertrophy" },
  { value: "strength", label: "Strength" },
  { value: "powerbuilding", label: "Powerbuilding" },
  { value: "general", label: "General" },
];

const DAYS: { value: number | "all"; label: string }[] = [
  { value: "all", label: "Any days" },
  { value: 3, label: "3 days" },
  { value: 4, label: "4 days" },
  { value: 5, label: "5 days" },
  { value: 6, label: "6 days" },
];

export default function ProgramsPage() {
  const [tab, setTab] = useState<Tab>("mine");
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <header className="flex items-end justify-between gap-4 pb-2">
        <h1 className="font-serif text-[32px] font-medium tracking-tight">Programs</h1>
        <Link
          href="/programs/new"
          className="bg-accent text-accent-foreground inline-flex h-[42px] items-center rounded-[var(--radius-button)] px-[18px] text-sm font-semibold tracking-[0.01em] hover:brightness-105"
        >
          New program
        </Link>
      </header>
      <div className="border-border flex gap-[18px] border-b">
        {(["mine", "templates"] as const).map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setTab(value)}
            className={`pb-[7px] -mb-px border-b-[1.5px] border-transparent text-xs font-semibold uppercase tracking-[0.08em] transition-colors duration-150 ease-out ${
              tab === value
                ? "text-text border-text"
                : "text-text-secondary hover:text-text"
            }`}
          >
            {value === "mine" ? "Mine" : "Templates"}
          </button>
        ))}
      </div>
      {tab === "mine" ? <MineTab /> : <TemplatesTab />}
    </div>
  );
}

function MineTab() {
  const list = useMyPrograms();
  if (list.isLoading) return <p className="text-text-secondary">Loading...</p>;
  if (list.isError) return <p className="text-destructive">Could not load programs.</p>;
  const items = list.data?.items ?? [];
  if (items.length === 0) {
    return (
      <Card>
        <CardContent>
          <p className="text-text-secondary mb-3">No programs yet.</p>
          <p className="text-text-secondary text-sm">
            Copy a template from the Templates tab, or click{" "}
            <span className="text-text">New program</span> above.
          </p>
        </CardContent>
      </Card>
    );
  }
  return (
    <ul className="flex flex-col gap-2">
      {items.map((p) => (
        <li key={p.id}>
          <Link
            href={`/programs/${p.id}`}
            className="hover:bg-surface border-border flex items-center justify-between rounded-[var(--radius-button)] border px-3 py-2"
          >
            <div className="flex min-w-0 flex-col">
              <span className="text-text truncate font-medium">{p.name}</span>
              <span className="text-text-tertiary text-xs">
                {p.goal} - {p.weeks}w x {p.days_per_week}d
              </span>
            </div>
            {p.is_active ? (
              <span className="text-accent inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)] px-[9px] text-[10px] font-semibold uppercase tracking-[0.1em]">
                Active
              </span>
            ) : null}
          </Link>
        </li>
      ))}
    </ul>
  );
}

function TemplatesTab() {
  const list = useTemplates();
  const [goal, setGoal] = useState<ProgramGoal | "all">("all");
  const [days, setDays] = useState<number | "all">("all");
  if (list.isLoading) return <p className="text-text-secondary">Loading...</p>;
  if (list.isError) return <p className="text-destructive">Could not load templates.</p>;
  const items = (list.data?.items ?? []).filter(
    (t: ProgramTemplateSummary) =>
      (goal === "all" || t.goal === goal) && (days === "all" || t.days_per_week === days),
  );
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-1">
        {GOALS.map((g) => (
          <Chip key={g.value} active={goal === g.value} onClick={() => setGoal(g.value)}>
            {g.label}
          </Chip>
        ))}
      </div>
      <div className="flex flex-wrap gap-1">
        {DAYS.map((d) => (
          <Chip key={d.value} active={days === d.value} onClick={() => setDays(d.value)}>
            {d.label}
          </Chip>
        ))}
      </div>
      <ul className="flex flex-col gap-2">
        {items.map((t) => (
          <li key={t.id}>
            <Link
              href={`/programs/templates/${t.slug}`}
              className="hover:bg-surface border-border flex items-center justify-between rounded-[var(--radius-button)] border px-3 py-2"
            >
              <div className="flex min-w-0 flex-col">
                <span className="text-text truncate font-medium">{t.name}</span>
                <span className="text-text-tertiary text-xs">
                  {t.goal} - {t.weeks}w x {t.days_per_week}d
                </span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold uppercase tracking-[0.1em] ${
        active
          ? "border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)] text-accent"
          : "border-border-strong text-text-secondary hover:text-text"
      }`}
    >
      {children}
    </button>
  );
}
