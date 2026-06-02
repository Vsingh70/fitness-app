"use client";

import { useParams, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useCopyTemplate, useTemplate } from "@/lib/hooks/programs";

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

  if (template.isLoading) return <p className="text-text-secondary">Loading...</p>;
  if (template.isError || !template.data)
    return <p className="text-destructive">Could not load template.</p>;

  const t = template.data;
  const days =
    (
      t.data as {
        days: {
          name: string;
          exercises: {
            slug_key: string;
            sets: number;
            reps_low?: number;
            reps_high?: number;
            rest_seconds?: number;
            notes?: string;
          }[];
        }[];
      }
    ).days ?? [];
  const slugMap = (t.data as { slug_map: Record<string, string> }).slug_map ?? {};

  const totalSets = days.reduce(
    (sum, day) => sum + day.exercises.reduce((s, ex) => s + ex.sets, 0),
    0,
  );

  const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      {/* Hero */}
      <div
        className="border-border bg-surface-elevated grid gap-6 rounded-[var(--radius-card)] border p-7 md:grid-cols-[1fr_auto]"
        style={{
          backgroundImage:
            "radial-gradient(800px 320px at 100% 0%, var(--color-accent-soft), transparent 60%)",
        }}
      >
        <div>
          <div className="text-text-tertiary text-[11px] font-semibold tracking-[0.1em] uppercase">
            Template · {t.goal}
          </div>
          <h1 className="mt-1 font-serif text-[32px] leading-tight font-medium tracking-tight">
            {t.name}
          </h1>
          <p className="text-text-secondary mt-2 max-w-[540px] text-sm leading-relaxed">
            {t.description ?? "Curated template."}
          </p>
          <div className="mt-4 flex flex-wrap gap-7">
            <Spec value={String(t.weeks)} label="weeks" />
            <Spec value={String(t.days_per_week)} label="days / wk" />
            <Spec value={t.goal} label="goal" capitalize />
          </div>
        </div>
        <div className="flex flex-col gap-2 self-end">
          <Button type="button" size="lg" onClick={onUse} disabled={copy.isPending}>
            {copy.isPending ? "Copying..." : "Use this template"}
          </Button>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <StatTile label="Days" value={String(t.days_per_week)} />
        <StatTile label="Weeks" value={String(t.weeks)} />
        <StatTile label="Sets / wk" value={String(totalSets)} />
      </div>

      {/* Week structure */}
      <div>
        <h2 className="text-text-secondary mb-3 text-[11px] font-semibold tracking-[0.14em] uppercase">
          Week structure
        </h2>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {days.map((day, idx) => (
            <Card key={`${day.name}-${idx}`} className="flex flex-col gap-2.5 p-[18px]">
              <div className="text-text-tertiary text-[10px] font-semibold tracking-[0.08em] uppercase">
                Day {idx + 1}
                {WEEKDAYS[idx] ? ` · ${WEEKDAYS[idx]}` : ""}
              </div>
              <div className="font-serif text-[18px] leading-none font-medium tracking-tight">
                {day.name}
              </div>
              <div className="mt-1 flex flex-col">
                {day.exercises.map((ex, j) => {
                  const realSlug = slugMap[ex.slug_key] ?? ex.slug_key;
                  return (
                    <div
                      key={j}
                      className="border-border flex items-center justify-between gap-3 border-b py-1.5 text-xs last:border-b-0"
                    >
                      <span className="text-text-secondary min-w-0 truncate capitalize">
                        {realSlug.replace(/-/g, " ")}
                      </span>
                      <span className="text-text-tertiary shrink-0 tabular-nums">
                        {ex.sets} × {ex.reps_low ?? "-"}
                        {ex.reps_high && ex.reps_high !== ex.reps_low ? `–${ex.reps_high}` : ""}
                      </span>
                    </div>
                  );
                })}
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
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
    <div className="text-text-secondary text-[13px]">
      <b
        className={`text-text block font-serif text-[18px] font-medium tabular-nums ${
          capitalize ? "capitalize" : ""
        }`}
      >
        {value}
      </b>
      {label}
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-border-strong flex flex-col gap-1.5 border-t pt-4">
      <span className="text-text-secondary text-[10px] font-semibold tracking-[0.12em] uppercase">
        {label}
      </span>
      <span className="text-text font-serif text-3xl font-medium tracking-tight tabular-nums">
        {value}
      </span>
    </div>
  );
}
