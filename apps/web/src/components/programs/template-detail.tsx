"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useCopyTemplate, useTemplate } from "@/lib/hooks/programs";

type TemplateDay = {
  name: string;
  exercises: {
    slug_key: string;
    sets: number;
    reps_low?: number;
    reps_high?: number;
  }[];
};

/**
 * Template preview (`.dw-*`): serif hero + spec strip + the day-by-day breakdown,
 * and a "Use this template" action that copies it into a new active program and
 * drops the user onto that program's overview.
 */
export function TemplateDetail({ slug }: { slug: string }) {
  const router = useRouter();
  const template = useTemplate(slug);
  const copy = useCopyTemplate();

  const onUse = () =>
    copy.mutate(slug, { onSuccess: (program) => router.push(`/programs/${program.id}`) });

  if (template.isLoading) return <p className="text-text-secondary">Loading…</p>;
  if (template.isError || !template.data)
    return <p className="text-destructive">Could not load template.</p>;

  const t = template.data;
  const days = (t.data as { days: TemplateDay[] }).days ?? [];
  const slugMap = (t.data as { slug_map: Record<string, string> }).slug_map ?? {};
  const goal = t.goal.replace(/_/g, " ");

  return (
    <div className="mx-auto flex max-w-4xl flex-col">
      <div className="mb-5 flex items-center justify-between gap-4">
        <p className="text-text-tertiary text-xs">
          <Link href="/programs" className="hover:text-text">
            Programs
          </Link>{" "}
          ›{" "}
          <Link href="/programs/templates" className="hover:text-text">
            Templates
          </Link>{" "}
          ›
        </p>
        <Button type="button" size="sm" onClick={onUse} disabled={copy.isPending}>
          {copy.isPending ? "Copying…" : "Use this template"}
        </Button>
      </div>

      <div className="dw-hero">
        <div className="dl">
          Template · <span className="capitalize">{goal}</span>
        </div>
        <h2>{t.name}</h2>
        {t.description ? <p>{t.description}</p> : null}
        <div className="dw-specs">
          <Spec value={String(t.weeks)} label="Weeks" />
          <Spec value={`${t.days_per_week}×`} label="Per week" />
          <Spec value={goal} label="Goal" capitalize />
        </div>
      </div>

      <div className="dw-days">
        {days.map((day, idx) => (
          <div className="dw-day" key={`${day.name}-${idx}`}>
            <div className="dl">Day {idx + 1}</div>
            <div className="nm">{day.name}</div>
            {day.exercises.map((ex, j) => {
              const realSlug = slugMap[ex.slug_key] ?? ex.slug_key;
              return (
                <div className="ex" key={j}>
                  <span className="nm-ex">{realSlug.replace(/-/g, " ")}</span>
                  <span className="sr">{schemeString(ex)}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function schemeString(ex: { sets: number; reps_low?: number; reps_high?: number }): string {
  if (ex.reps_low == null) return `${ex.sets}×`;
  const reps =
    ex.reps_high && ex.reps_high !== ex.reps_low
      ? `${ex.reps_low}–${ex.reps_high}`
      : String(ex.reps_low);
  return `${ex.sets}×${reps}`;
}

function Spec({
  value,
  label,
  capitalize,
}: {
  value: string;
  label: string;
  capitalize?: boolean;
}) {
  return (
    <div className="s">
      <div className={`v ${capitalize ? "capitalize" : ""}`}>{value}</div>
      <div className="l">{label}</div>
    </div>
  );
}
