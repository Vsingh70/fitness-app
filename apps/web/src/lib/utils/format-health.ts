import { toNum } from "@/lib/utils/format-weight";

const EMDASH = "—";

/** 12438 -> "12,438"; null/undefined -> "—". */
export function formatSteps(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return EMDASH;
  return Math.round(n).toLocaleString("en-US");
}

/** 444 -> "7h 24m"; 0 -> "0h 0m"; <60 -> "0h 5m"; null/undefined -> "—". */
export function formatSleep(minutes: number | null | undefined): string {
  if (minutes == null || !Number.isFinite(minutes)) return EMDASH;
  const total = Math.max(0, Math.round(minutes));
  const h = Math.floor(total / 60);
  const m = total % 60;
  return `${h}h ${m}m`;
}

/** minutes -> hours, 1dp, for charting. null/undefined -> null (drop the point). */
export function sleepHours(minutes: number | null | undefined): number | null {
  if (minutes == null || !Number.isFinite(minutes)) return null;
  return Math.round((minutes / 60) * 10) / 10;
}

/** 54 -> "54 bpm"; null -> "—". */
export function formatHr(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return EMDASH;
  return `${Math.round(n)} bpm`;
}

/** hrv_ms is a DECIMAL-as-STRING. "48.2" -> "48 ms"; null/""/garbage -> "—". */
export function formatHrv(hrv: string | number | null | undefined): string {
  const n = toNum(hrv);
  if (n === null) return EMDASH;
  return `${Math.round(n)} ms`;
}
