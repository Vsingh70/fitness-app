"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

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

export default function TemplateDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const template = useTemplate(slug);
  const copy = useCopyTemplate();

  const onUse = () => {
    copy.mutate(slug, {
      onSuccess: (program) => router.push(`/programs/${program.id}`),
    });
  };

  if (template.isLoading) return <p className="text-text-secondary">Loading…</p>;
  if (template.isError || !template.data)
    return <p className="text-destructive">Could not load template.</p>;

  const t = template.data;
  const days = (t.data as { days: TemplateDay[] }).days ?? [];
  const slugMap = (t.data as { slug_map: Record<string, string> }).slug_map ?? {};
  const goal = t.goal.replace(/_/g, " ");

  return (
    <div className="mx-auto flex max-w-4xl flex-col">
      {/* Top chrome: breadcrumb + Use this template */}
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

      {/* Hero */}
      <div className="border-text border-b-2 pb-4">
        <div className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
          Template · <span className="capitalize">{goal}</span>
        </div>
        <h1 className="mt-1.5 mb-2 font-serif text-[34px] leading-tight font-medium tracking-[-0.02em]">
          {t.name}
        </h1>
        {t.description ? (
          <p className="text-text-secondary max-w-[540px] text-sm leading-[1.55]">
            {t.description}
          </p>
        ) : null}
        <div className="mt-4 flex gap-[30px]">
          <Spec value={String(t.weeks)} label="Weeks" />
          <Spec value={`${t.days_per_week}×`} label="Per week" />
          <Spec value={goal} label="Goal" capitalize />
        </div>
      </div>

      {/* Day-by-day breakdown */}
      <div className="mt-6 columns-1 [column-gap:24px] md:columns-3">
        {days.map((day, idx) => (
          <div key={`${day.name}-${idx}`} className="mb-0 break-inside-avoid pb-[18px]">
            <div className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
              Day {idx + 1}
            </div>
            <div className="mt-1 mb-1.5 font-serif text-[17px]">{day.name}</div>
            {day.exercises.map((ex, j) => {
              const realSlug = slugMap[ex.slug_key] ?? ex.slug_key;
              return (
                <div
                  key={j}
                  className="border-border flex items-center justify-between gap-3 border-b py-1 text-xs last:border-b-0"
                >
                  <span className="min-w-0 truncate capitalize">{realSlug.replace(/-/g, " ")}</span>
                  <span className="text-text-tertiary shrink-0 font-serif tabular-nums">
                    {schemeString(ex)}
                  </span>
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
  return `${ex.sets} × ${reps}`;
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
    <div>
      <div className={`font-serif text-[19px] tabular-nums ${capitalize ? "capitalize" : ""}`}>
        {value}
      </div>
      <div className="text-text-tertiary text-[10px] font-semibold tracking-[0.1em] uppercase">
        {label}
      </div>
    </div>
  );
}
