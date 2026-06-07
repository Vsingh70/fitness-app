"use client";

import Link from "next/link";
import { useState } from "react";

import { useHealthStatus } from "@/lib/hooks/health";

/**
 * App-level prompt shown when the Fitbit (Google Health) authorization has
 * expired (the 7-day Testing-mode refresh token dies, surfaced server-side as
 * `needs_reauth`). Without this, auto-sync would silently go stale. Dismissible
 * for the session; it returns next load while the connection still needs reauth.
 */
export function ReconnectBanner() {
  const { data } = useHealthStatus();
  const [dismissed, setDismissed] = useState(false);

  if (!data?.needs_reauth || dismissed) return null;

  return (
    <div
      role="alert"
      className="border-destructive/40 bg-destructive-soft text-text mb-4 flex items-center justify-between gap-3 rounded-[var(--radius-card)] border px-4 py-3"
    >
      <div className="min-w-0 text-sm">
        <span className="font-semibold">Reconnect Fitbit</span>
        <span className="text-text-secondary">
          {" "}
          — your watch authorization expired, so new data isn’t syncing.
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Link
          href="/settings#connections"
          className="bg-accent text-accent-foreground rounded-[var(--radius-button)] px-3 py-1.5 text-sm font-semibold"
        >
          Reconnect
        </Link>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss"
          className="text-text-tertiary hover:text-text text-sm font-medium"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
