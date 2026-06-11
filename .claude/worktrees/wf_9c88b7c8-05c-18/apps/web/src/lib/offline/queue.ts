"use client";

import localforage from "localforage";

import type { SetCreate } from "@/lib/workouts/types";
import { addSet } from "@/lib/api/workouts";

/**
 * Best-effort offline queue for mutations issued while a session is in progress.
 * We use the same Idempotency-Key for each retry so the server dedupes when the
 * original request actually reached it.
 *
 * Scope today: SetCreate ops only (the highest-volume in-session write).
 */

type QueuedOp = {
  kind: "add_set";
  workoutExerciseId: string;
  body: SetCreate;
  idempotencyKey: string;
  queuedAt: number;
};

const STORE_KEY = "workout-offline-queue";

let store: LocalForage | null = null;
function getStore(): LocalForage {
  if (store) return store;
  store = localforage.createInstance({
    name: "gym",
    storeName: "offline",
    description: "Per-user offline write queue",
  });
  return store;
}

async function readQueue(): Promise<QueuedOp[]> {
  return (await getStore().getItem<QueuedOp[]>(STORE_KEY)) ?? [];
}

async function writeQueue(queue: QueuedOp[]): Promise<void> {
  await getStore().setItem(STORE_KEY, queue);
}

export async function enqueue(op: QueuedOp): Promise<void> {
  const queue = await readQueue();
  queue.push(op);
  await writeQueue(queue);
}

export async function queueLength(): Promise<number> {
  return (await readQueue()).length;
}

/** Try to flush every queued op. Returns the number of successfully flushed ops. */
export async function flushQueue(): Promise<number> {
  const queue = await readQueue();
  if (queue.length === 0) return 0;
  const remaining: QueuedOp[] = [];
  let flushed = 0;
  for (const op of queue) {
    try {
      if (op.kind === "add_set") {
        await addSet(op.workoutExerciseId, op.body, op.idempotencyKey);
        flushed += 1;
      }
    } catch {
      remaining.push(op);
    }
  }
  await writeQueue(remaining);
  return flushed;
}

let listenerInstalled = false;
export function installOnlineFlush(onFlush?: (count: number) => void): () => void {
  if (typeof window === "undefined" || listenerInstalled) return () => undefined;
  listenerInstalled = true;
  const handler = () => {
    void flushQueue().then((n) => {
      if (n > 0) onFlush?.(n);
    });
  };
  window.addEventListener("online", handler);
  return () => {
    window.removeEventListener("online", handler);
    listenerInstalled = false;
  };
}
