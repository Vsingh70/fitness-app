"use client";

import Link from "next/link";
import { useState } from "react";

import { Card } from "@/components/ui/card";
import { useMyPrograms, useTemplates } from "@/lib/hooks/programs";
import type { ProgramGoal, ProgramListItem, ProgramTemplateSummary } from "@/lib/programs/types";

const GOALS: { value: ProgramGoal | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "hypertrophy", label: "Hypertrophy" },
  { value: "strength", label: "Strength" },
  { value: "powerbuilding", label: "Powerbuilding" },
  { value: "general", label: "General" },
];

export default function ProgramsPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-8">
      <header className="flex items-end justify-between gap-4">
        <h1 className="font-serif text-[32px] font-medium tracking-tight">Programs</h1>
        <Link
          href="/programs/new"
          className="bg-accent text-accent-foreground inline-flex h-[42px] items-center rounded-[var(--radius-button)] px-[18px] text-sm font-semibold tracking-[0.01em] hover:brightness-105"
        >
          New program
        </Link>
      </header>

      <ActiveProgram />
      <Templates />
      <MyPrograms />
    </div>
  );
}

function ActiveProgram() {
  const list = useMyPrograms();
  const active = (list.data?.items ?? []).find((p) => p.is_active);
  if (!active) return null;

  return (
    <Link
      href={`/programs/${active.id}`}
      className="border-border bg-surface-elevated block rounded-[var(--radius-card)] border p-6 transition-colors hover:brightness-[1.01]"
      style={{
        backgroundImage:
          "radial-gradient(600px 280px at 100% 0%, var(--color-accent-soft), transparent 60%)",
      }}
    >
      <div className="text-text-tertiary text-[11px] font-semibold tracking-[0.1em] uppercase">
        Active program
      </div>
      <div className="mt-1 mb-3 font-serif text-[28px] leading-tight font-medium tracking-tight">
        {active.name}
      </div>
      <div className="flex flex-wrap gap-6">
        <Meta value={active.goal} label="Goal" capitalize />
        <Meta value={`${active.days_per_week}×/week`} label="Frequency" />
        <Meta value={`${active.weeks} weeks`} label="Length" />
        {active.activated_at ? (
          <Meta
            value={new Date(active.activated_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
            })}
            label="Started"
          />
        ) : null}
      </div>
    </Link>
  );
}

function Meta({
  value,
  label,
  capitalize,
}: {
  value: string;
  label: string;
  capitalize?: boolean;
}) {
  return (
    <div className="text-text-secondary text-[13px]">
      <b
        className={`text-text block font-serif text-base font-medium tabular-nums ${
          capitalize ? "capitalize" : ""
        }`}
      >
        {value}
      </b>
      {label}
    </div>
  );
}

function Templates() {
  const list = useTemplates();
  const [goal, setGoal] = useState<ProgramGoal | "all">("all");

  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-text-secondary text-sm font-semibold">Templates</h2>
        <div className="border-border bg-surface inline-flex gap-0.5 rounded-[var(--radius-pill)] border p-0.5">
          {GOALS.map((g) => (
            <button
              key={g.value}
              type="button"
              onClick={() => setGoal(g.value)}
              className={`rounded-[var(--radius-pill)] px-3 py-1 text-xs font-medium transition-colors duration-150 ease-out ${
                goal === g.value
                  ? "bg-surface-elevated text-text shadow-[var(--shadow-1)]"
                  : "text-text-secondary hover:text-text"
              }`}
            >
              {g.label}
            </button>
          ))}
        </div>
      </div>

      {list.isLoading ? (
        <p className="text-text-secondary">Loading...</p>
      ) : list.isError ? (
        <p className="text-destructive">Could not load templates.</p>
      ) : (
        <TemplateGrid items={list.data?.items ?? []} goal={goal} />
      )}
    </section>
  );
}

function TemplateGrid({
  items,
  goal,
}: {
  items: ProgramTemplateSummary[];
  goal: ProgramGoal | "all";
}) {
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
          className="border-border bg-surface-elevated flex h-full flex-col gap-2 rounded-[var(--radius-card)] border p-[18px] transition-[box-shadow,transform] duration-150 ease-out hover:-translate-y-0.5 hover:shadow-[var(--shadow-2)]"
        >
          <div className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] capitalize uppercase">
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

function MyPrograms() {
  const list = useMyPrograms();
  if (list.isLoading) return <p className="text-text-secondary">Loading...</p>;
  if (list.isError) return <p className="text-destructive">Could not load programs.</p>;
  const items = list.data?.items ?? [];

  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-text-secondary text-sm font-semibold">My programs</h2>
        {items.length > 0 ? (
          <span className="text-text-tertiary text-xs">
            {items.length} program{items.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>

      {items.length === 0 ? (
        <Card className="px-[18px] py-5">
          <p className="text-text-secondary mb-1.5">No programs yet.</p>
          <p className="text-text-secondary text-sm">
            Copy a template above, or click{" "}
            <span className="text-text font-medium">New program</span>.
          </p>
        </Card>
      ) : (
        <Card className="divide-border flex flex-col divide-y">
          {items.map((p) => (
            <ProgramRow key={p.id} program={p} />
          ))}
        </Card>
      )}
    </section>
  );
}

function ProgramRow({ program: p }: { program: ProgramListItem }) {
  return (
    <Link
      href={`/programs/${p.id}`}
      className="hover:bg-surface flex items-center gap-3 px-[18px] py-3.5 transition-colors first:rounded-t-[var(--radius-card)] last:rounded-b-[var(--radius-card)]"
    >
      <div className="min-w-0 flex-1">
        <div className="text-text truncate font-medium">{p.name}</div>
        <div className="text-text-tertiary mt-0.5 text-xs">
          {p.source === "manual" ? "Custom" : "Copied from template"} · created{" "}
          {new Date(p.created_at).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          })}
        </div>
      </div>
      {p.is_active ? (
        <span className="text-accent inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border border-[color-mix(in_oklab,var(--color-accent)_45%,transparent)] px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
          Active
        </span>
      ) : (
        <span className="text-text-secondary border-border-strong inline-flex h-[22px] items-center rounded-[var(--radius-pill)] border px-[9px] text-[10px] font-semibold tracking-[0.1em] uppercase">
          Inactive
        </span>
      )}
      <span className="text-text-tertiary shrink-0 text-xs capitalize">
        {p.goal} · {p.weeks}w × {p.days_per_week}d
      </span>
    </Link>
  );
}
