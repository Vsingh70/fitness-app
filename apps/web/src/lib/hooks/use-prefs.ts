"use client";

import { useSyncExternalStore } from "react";

/**
 * Client-only display preferences that have no server field yet.
 * Weight unit is derived from the server `unit_system` (see settings page);
 * these are the extras the settings prototype exposes.
 */
export type Distance = "km" | "mi";
export type Density = "regular" | "compact";

interface Prefs {
  distance: Distance;
  density: Density;
  restTimerSeconds: number;
}

const KEY = "om.prefs";

const DEFAULTS: Prefs = {
  distance: "km",
  density: "regular",
  restTimerSeconds: 120,
};

const listeners = new Set<() => void>();
let cache: Prefs | null = null;

function read(): Prefs {
  if (typeof window === "undefined") return DEFAULTS;
  if (cache) return cache;
  try {
    const raw = window.localStorage.getItem(KEY);
    cache = raw ? { ...DEFAULTS, ...(JSON.parse(raw) as Partial<Prefs>) } : DEFAULTS;
  } catch {
    cache = DEFAULTS;
  }
  return cache;
}

function write(next: Prefs) {
  cache = next;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  }
  listeners.forEach((l) => l());
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

export function usePrefs(): Prefs & {
  setPref: <K extends keyof Prefs>(key: K, value: Prefs[K]) => void;
} {
  const prefs = useSyncExternalStore(subscribe, read, () => DEFAULTS);
  return {
    ...prefs,
    setPref: (key, value) => write({ ...read(), [key]: value }),
  };
}
