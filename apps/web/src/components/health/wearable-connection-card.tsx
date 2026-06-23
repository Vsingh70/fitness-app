"use client";

import { Activity } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import {
  useConnectHealth,
  useDisconnectHealth,
  useHealthStatus,
  useSyncHealth,
} from "@/lib/hooks/health";

/** Relative "x ago" for the last-sync timestamp; "never" when unsynced. */
function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "never";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  return `${Math.round(hrs / 24)} d ago`;
}

/**
 * The single connection card/status for the Wearable section: the active
 * Fitbit→Google Health provider. Source of truth for the wearable connection
 * lives on Health (Settings defers here). Connect / Sync / Reconnect /
 * Disconnect mirror the Settings affordances without the ECG spike probe.
 */
export function WearableConnectionCard() {
  const statusQuery = useHealthStatus();
  const health = statusQuery.data;
  const connect = useConnectHealth();
  const disconnect = useDisconnectHealth();
  const sync = useSyncHealth();
  const pushToast = useToastStore((s) => s.push);

  const status = statusQuery.isLoading
    ? "Checking…"
    : health?.needs_reauth
      ? "Reconnect needed · authorization expired"
      : health?.connected
        ? `Connected · synced ${relativeTime(health.last_synced_at)}`
        : "Not connected";

  return (
    <Card>
      <div className="grid grid-cols-[44px_1fr_auto] items-center gap-4 p-[18px]">
        <div className="bg-surface text-text-secondary grid h-11 w-11 place-items-center rounded-[10px]">
          <Activity className="h-[22px] w-[22px]" strokeWidth={1.6} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold">Fitbit (via Google)</div>
          <div
            className={
              health?.needs_reauth
                ? "text-destructive mt-0.5 text-xs"
                : "text-text-tertiary mt-0.5 text-xs"
            }
          >
            {status}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {health?.needs_reauth ? (
            <>
              <Button
                size="sm"
                disabled={connect.isPending}
                onClick={() =>
                  connect.mutate(undefined, {
                    onError: (e) =>
                      pushToast({
                        kind: "error",
                        message: (e as unknown as ApiError)?.message ?? "Could not start reconnect",
                      }),
                  })
                }
              >
                {connect.isPending ? "Starting…" : "Reconnect"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={disconnect.isPending}
                onClick={() => disconnect.mutate()}
              >
                Disconnect
              </Button>
            </>
          ) : health?.connected ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                disabled={sync.isPending}
                onClick={() =>
                  sync.mutate(undefined, {
                    onSuccess: (r) => {
                      const total = r.weight_written + r.body_fat_written;
                      pushToast({
                        kind: "success",
                        message:
                          total > 0
                            ? `Synced ${total} new reading${total === 1 ? "" : "s"}`
                            : "Already up to date",
                      });
                    },
                    onError: (e) =>
                      pushToast({
                        kind: "error",
                        message: (e as unknown as ApiError)?.message ?? "Sync failed",
                      }),
                  })
                }
              >
                {sync.isPending ? "Syncing…" : "Sync now"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={disconnect.isPending}
                onClick={() => disconnect.mutate()}
              >
                Disconnect
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              disabled={connect.isPending}
              onClick={() =>
                connect.mutate(undefined, {
                  onError: (e) =>
                    pushToast({
                      kind: "error",
                      message: (e as unknown as ApiError)?.message ?? "Could not start connect",
                    }),
                })
              }
            >
              {connect.isPending ? "Starting…" : "Connect"}
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
