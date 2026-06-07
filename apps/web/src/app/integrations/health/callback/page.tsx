"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import type { ApiError } from "@/lib/api/client";
import { HEALTH_VERIFIER_KEY, useCompleteHealthCallback } from "@/lib/hooks/health";

function HealthCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const complete = useCompleteHealthCallback();
  const ran = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const code = params.get("code");
    const state = params.get("state");
    const denied = params.get("error");
    const verifier = window.localStorage.getItem(HEALTH_VERIFIER_KEY);

    if (denied) {
      setError("Authorization was cancelled.");
      return;
    }
    if (!code || !state || !verifier) {
      setError("Missing authorization details. Please try connecting again.");
      return;
    }

    complete.mutate(
      { code, state, code_verifier: verifier },
      {
        onSuccess: () => {
          window.localStorage.removeItem(HEALTH_VERIFIER_KEY);
          router.replace("/settings#connections");
        },
        onError: (e) => setError((e as unknown as ApiError)?.message ?? "Failed to connect."),
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      {error ? (
        <>
          <p className="text-destructive max-w-sm text-sm">{error}</p>
          <Button onClick={() => router.replace("/settings#connections")}>Back to settings</Button>
        </>
      ) : (
        <p className="text-text-secondary">Connecting Fitbit (via Google)…</p>
      )}
    </div>
  );
}

export default function HealthCallbackPage() {
  return (
    <Suspense
      fallback={<div className="flex min-h-screen items-center justify-center px-4">Loading…</div>}
    >
      <HealthCallbackInner />
    </Suspense>
  );
}
