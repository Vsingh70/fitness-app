import type { components } from "@/lib/api/types";

type UnitSystem = components["schemas"]["UnitSystem"]; // "metric" | "imperial"
type BodyMetric = components["schemas"]["BodyMetricResponse"];

export const KG_PER_LB = 2.20462;

/** Strict parser for DECIMAL-as-string fields. null for null/undefined/""/non-finite. */
export function toNum(v: string | number | null | undefined): number | null {
  if (v === null || v === undefined) return null;
  if (typeof v === "string" && v.trim() === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/** Round to 1 decimal place. */
export function round1(n: number): number {
  const r = Math.round(n * 10) / 10;
  // Normalize -0 to 0 so a tiny change that rounds to zero never renders a
  // signed "−0" or a misleading down arrow.
  return r === 0 ? 0 : r;
}

/** kg label vs lb label. Defaults to metric when unit is undefined (pre-`me` load). */
export function weightUnitLabel(unit: UnitSystem | undefined): "kg" | "lb" {
  return unit === "imperial" ? "lb" : "kg";
}

/** Read path: kg (string|number|null) -> display NUMBER in the user's unit, rounded 1dp. null if missing. */
export function kgToDisplay(
  kg: string | number | null | undefined,
  unit: UnitSystem | undefined,
): number | null {
  const n = toNum(kg);
  if (n === null) return null;
  const converted = unit === "imperial" ? n * KG_PER_LB : n;
  return round1(converted);
}

/** Write path: display value -> kg. NOT rounded (backend stores full precision). */
export function displayToKg(value: number, unit: UnitSystem | undefined): number {
  return unit === "imperial" ? value / KG_PER_LB : value;
}

/** "72.4 kg" / "159.6 lb" — full formatted string. "—" when missing. */
export function formatWeight(
  kg: string | number | null | undefined,
  unit: UnitSystem | undefined,
): string {
  const d = kgToDisplay(kg, unit);
  return d === null ? "—" : `${d} ${weightUnitLabel(unit)}`;
}

/**
 * Weekly delta in DISPLAY units (rounded 1dp) and the raw-kg sign.
 * From the newest-first list: latest = first row with non-null weight_kg;
 * prior = first SUBSEQUENT row with non-null weight whose recorded_at is >= 7 days
 * older than latest.recorded_at; fallback = oldest non-null-weight row.
 * Returns null when fewer than 2 usable (weighted) rows exist.
 */
export function weeklyDelta(
  items: BodyMetric[] | undefined,
  unit: UnitSystem | undefined,
): { displayDelta: number; kgDelta: number } | null {
  if (!items || items.length === 0) return null;
  const weighted = items.filter((r) => toNum(r.weight_kg) !== null); // still newest-first
  if (weighted.length < 2) return null;
  const latest = weighted[0]!;
  const latestKg = toNum(latest.weight_kg)!;
  const latestTime = new Date(latest.recorded_at).getTime();
  const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;
  const prior =
    weighted.slice(1).find((r) => latestTime - new Date(r.recorded_at).getTime() >= sevenDaysMs) ??
    weighted[weighted.length - 1]!; // fallback: oldest weighted row
  const priorKg = toNum(prior.weight_kg)!;
  const kgDelta = latestKg - priorKg; // raw sign source
  const displayDelta = round1(
    (unit === "imperial" ? latestKg * KG_PER_LB : latestKg) -
      (unit === "imperial" ? priorKg * KG_PER_LB : priorKg),
  );
  return { displayDelta, kgDelta };
}

/** date-only or datetime ISO -> "Jun 6". Date-only strings are anchored to local midnight to avoid TZ shift. */
export function formatShortDate(iso: string): string {
  const d = iso.length === 10 ? new Date(`${iso}T00:00:00`) : new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** "Today" / "Yesterday" / "3d ago" (<7 days) else "Jun 6". */
export function relativeDate(iso: string): string {
  const d = iso.length === 10 ? new Date(`${iso}T00:00:00`) : new Date(iso);
  const now = new Date();
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const days = Math.round((startOf(now) - startOf(d)) / (24 * 60 * 60 * 1000));
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;
  return formatShortDate(iso);
}
