"use client";

import { useParams, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
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

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{t.name}</h1>
          <p className="text-text-secondary mt-1">{t.description ?? "Curated template."}</p>
          <p className="text-text-tertiary mt-1 text-xs">
            {t.goal} - {t.weeks} weeks x {t.days_per_week} days/week
          </p>
        </div>
        <Button type="button" onClick={onUse} disabled={copy.isPending}>
          {copy.isPending ? "Copying..." : "Use this program"}
        </Button>
      </header>

      {days.map((day, idx) => (
        <Card key={`${day.name}-${idx}`}>
          <CardHeader>
            <h2 className="text-lg font-semibold">
              Day {idx + 1}: {day.name}
            </h2>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {day.exercises.map((ex, j) => {
              const realSlug = slugMap[ex.slug_key] ?? ex.slug_key;
              return (
                <div
                  key={j}
                  className="border-border flex items-center justify-between border-t pt-2 text-sm first:border-t-0 first:pt-0"
                >
                  <div className="flex flex-col">
                    <span className="text-text font-medium">{realSlug}</span>
                    {ex.notes ? (
                      <span className="text-text-tertiary text-xs">{ex.notes}</span>
                    ) : null}
                  </div>
                  <span className="text-text-secondary tabular-nums">
                    {ex.sets} x {ex.reps_low ?? "-"}
                    {ex.reps_high && ex.reps_high !== ex.reps_low ? `-${ex.reps_high}` : ""}
                    {ex.rest_seconds ? ` / ${ex.rest_seconds}s rest` : ""}
                  </span>
                </div>
              );
            })}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
