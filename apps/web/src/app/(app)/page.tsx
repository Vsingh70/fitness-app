"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useCreateEmptySession, useRecentSessions } from "@/lib/hooks/workouts";
import { useActiveSession } from "@/lib/state/active-session";

export default function TodayPage() {
  const router = useRouter();
  const recent = useRecentSessions(5);
  const create = useCreateEmptySession();
  const setActive = useActiveSession((s) => s.setActive);

  const startEmpty = () => {
    create.mutate(
      {},
      {
        onSuccess: (session) => {
          setActive(session.id, session.started_at);
          router.push(`/workouts/${session.id}`);
        },
      },
    );
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Today</h1>
        <p className="text-text-secondary mt-1">Start a workout or pick up where you left off.</p>
      </header>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Up next</h2>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-text-secondary">
            Scheduled workouts land in the programming phase. For now, start an empty session.
          </p>
          <Button
            type="button"
            size="lg"
            onClick={startEmpty}
            disabled={create.isPending}
            data-testid="start-empty-workout"
          >
            {create.isPending ? "Starting..." : "Start empty workout"}
          </Button>
        </CardContent>
      </Card>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Recent sessions</h2>
        {recent.isLoading ? (
          <p className="text-text-secondary">Loading...</p>
        ) : recent.isError ? (
          <p className="text-destructive">Could not load sessions.</p>
        ) : recent.data && recent.data.items.length === 0 ? (
          <p className="text-text-secondary">No sessions yet. Start one above.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {recent.data?.items.map((s) => (
              <li key={s.id}>
                <a
                  href={`/workouts/${s.id}`}
                  className="hover:bg-surface border-border flex items-center justify-between rounded-[var(--radius-button)] border px-3 py-2"
                >
                  <span className="font-medium">{s.name ?? "Untitled session"}</span>
                  <span className="text-text-tertiary text-xs">
                    {new Date(s.started_at).toLocaleString()}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Recent PRs</h2>
        <p className="text-text-secondary text-sm">PR cards land with the analytics phase.</p>
      </section>
    </div>
  );
}
