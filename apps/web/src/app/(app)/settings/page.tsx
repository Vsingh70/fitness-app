"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { RevealGroup, RevealItem } from "@/components/motion/RevealGroup";
import { SegControl, SettingRow } from "@/components/settings/controls";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import { useToastStore } from "@/components/ui/toast";
import type { ApiError } from "@/lib/api/client";
import { useHealthStatus } from "@/lib/hooks/health";
import { useDeleteAccount, useMe, useUpdateMe } from "@/lib/hooks/me";
import { usePrefs } from "@/lib/hooks/use-prefs";
import { useDeactivateAnyProgram, useMyPrograms } from "@/lib/hooks/programs";
import { ACCENTS, useThemeStore, type Accent, type Theme } from "@/lib/hooks/use-theme";

const ACCENT_SWATCH: Record<Accent, string> = {
  blue: "oklch(0.545 0.108 48)",
  indigo: "oklch(0.480 0.052 264)",
  mint: "oklch(0.520 0.058 196)",
  orange: "oklch(0.605 0.092 72)",
  pink: "oklch(0.520 0.094 12)",
};

const ACCENT_LABEL: Record<Accent, string> = {
  blue: "Clay",
  indigo: "Slate",
  mint: "Teal",
  orange: "Ochre",
  pink: "Rose",
};

const NAV = [
  {
    group: "Account",
    items: [
      { id: "profile", label: "Profile" },
      { id: "appearance", label: "Appearance" },
      { id: "units", label: "Units & defaults" },
    ],
  },
  { group: "Training", items: [{ id: "training", label: "Active program" }] },
  { group: "Nutrition", items: [{ id: "nutrition", label: "Tracking mode" }] },
  { group: "Integrations", items: [{ id: "connections", label: "Connected services" }] },
  { group: "Data", items: [{ id: "data", label: "Export & delete" }] },
  { group: "App", items: [{ id: "about", label: "Help & about" }] },
];

function formatRest(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function parseRest(value: string): number | null {
  const m = value.match(/^(\d+):([0-5]?\d)$/);
  if (!m) return null;
  return Number(m[1]) * 60 + Number(m[2]);
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "never";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const diff = Date.now() - then;
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  return `${Math.round(hrs / 24)} d ago`;
}

export default function SettingsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const pushToast = useToastStore((s) => s.push);

  const meQuery = useMe();
  const updateMe = useUpdateMe();
  const { theme, accent, setTheme, setAccent } = useThemeStore();
  const prefs = usePrefs();
  const programsQuery = useMyPrograms();
  const healthQuery = useHealthStatus();
  const health = healthQuery.data;
  const deactivate = useDeactivateAnyProgram();
  const deleteAccount = useDeleteAccount();

  const [active, setActive] = useState("profile");
  const [restDraft, setRestDraft] = useState(formatRest(prefs.restTimerSeconds));
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    setRestDraft(formatRest(prefs.restTimerSeconds));
  }, [prefs.restTimerSeconds]);

  const signOut = useMutation({
    mutationFn: async () => {
      await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    },
    onSuccess: () => {
      qc.clear();
      router.push("/sign-in");
    },
  });

  if (meQuery.isLoading) {
    return <div className="text-text-secondary py-10 text-center text-sm">Loading…</div>;
  }
  if (meQuery.isError) {
    const err = meQuery.error as unknown as ApiError;
    if (err?.status === 401) {
      router.push("/sign-in");
      return null;
    }
    return (
      <div className="text-destructive py-10 text-center text-sm">
        Failed to load profile: {err?.message}
      </div>
    );
  }

  const me = meQuery.data!;
  const programs = programsQuery.data?.items ?? [];
  const activeProgram = programs.find((p) => p.is_active);
  const inactivePrograms = programs.filter((p) => !p.is_active);

  const healthStatus = healthQuery.isLoading
    ? "Checking…"
    : health?.needs_reauth
      ? "Reconnect needed · authorization expired"
      : health?.connected
        ? `Connected · synced ${relativeTime(health.last_synced_at)}`
        : "Not connected";

  const patchMe = (body: Parameters<typeof updateMe.mutate>[0], label: string) =>
    updateMe.mutate(body, {
      onSuccess: () => pushToast({ kind: "success", message: `${label} updated` }),
      onError: (e) =>
        pushToast({
          kind: "error",
          message: `Couldn't update ${label.toLowerCase()}: ${(e as unknown as ApiError)?.message ?? ""}`,
        }),
    });

  const initials = (me.display_name ?? me.email ?? "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");

  const commitRest = () => {
    const seconds = parseRest(restDraft);
    if (seconds == null) {
      pushToast({ kind: "error", message: "Use mm:ss, e.g. 2:00" });
      setRestDraft(formatRest(prefs.restTimerSeconds));
      return;
    }
    prefs.setPref("restTimerSeconds", seconds);
    pushToast({ kind: "success", message: "Rest timer saved" });
  };

  return (
    <div className="page-shell grid gap-[var(--space-section)] md:grid-cols-[200px_minmax(0,1fr)] md:gap-10">
      <nav className="top-[88px] hidden h-max flex-col gap-0.5 md:sticky md:flex">
        {NAV.map((section) => (
          <div key={section.group}>
            <div className="text-text-tertiary px-3 pt-3.5 pb-1.5 text-[10px] font-bold tracking-[0.12em] uppercase">
              {section.group}
            </div>
            {section.items.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                onClick={() => setActive(item.id)}
                className={
                  "block rounded-lg px-3 py-2 text-[13px] font-medium transition-colors " +
                  (active === item.id
                    ? "bg-surface text-text"
                    : "text-text-secondary hover:bg-surface")
                }
              >
                {item.label}
              </a>
            ))}
          </div>
        ))}
      </nav>

      <div className="min-w-0">
        <RevealGroup className="flex flex-col gap-[var(--space-section)]">
          <RevealItem>
            <header>
              <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.14em] uppercase">
                Account
              </span>
              <h1
                className="text-text mt-1 font-serif font-medium tracking-tight"
                style={{ fontSize: "var(--text-h2)" }}
              >
                Settings
              </h1>
            </header>
          </RevealItem>

          {/* Profile */}
          <RevealItem>
            <Section
              id="profile"
              title="Profile"
              sub="How you show up in the app. Display name only — no public profiles."
            >
              <Card>
                <div className="flex items-center gap-5 p-5">
                  <div className="grid h-16 w-16 place-items-center rounded-full bg-[linear-gradient(135deg,var(--color-accent),var(--color-accent-soft))] font-serif text-[22px] font-semibold text-white">
                    {initials || "?"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[17px] font-semibold">
                      {me.display_name ?? "No name set"}
                    </div>
                    <div className="text-text-tertiary mt-0.5 truncate text-[13px]">
                      {me.email ?? "Email hidden"}
                    </div>
                  </div>
                </div>
                <SettingRow title="Display name">
                  <Input
                    className="h-[34px] w-[200px]"
                    defaultValue={me.display_name ?? ""}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v !== (me.display_name ?? ""))
                        patchMe({ display_name: v || null }, "Display name");
                    }}
                  />
                </SettingRow>
                <SettingRow title="Birthdate" sub="Used to compute Mifflin-St Jeor defaults">
                  <Input
                    type="date"
                    className="h-[34px] w-[160px]"
                    defaultValue={me.birthdate ?? ""}
                    onBlur={(e) => {
                      const v = e.target.value || null;
                      if (v !== (me.birthdate ?? null)) patchMe({ birthdate: v }, "Birthdate");
                    }}
                  />
                </SettingRow>
                <SettingRow title="Time zone" sub="Workout reminders use this">
                  <Input
                    className="h-[34px] w-[200px]"
                    defaultValue={me.timezone}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v && v !== me.timezone) patchMe({ timezone: v }, "Time zone");
                    }}
                  />
                </SettingRow>
              </Card>
            </Section>
          </RevealItem>

          {/* Appearance */}
          <RevealItem>
            <Section
              id="appearance"
              title="Appearance"
              sub="Pick a theme and an accent. Changes apply live across every screen."
            >
              <Card>
                <SettingRow title="Theme" sub="Auto follows your system preference">
                  <SegControl<Theme>
                    aria-label="Theme"
                    value={theme}
                    onChange={setTheme}
                    options={[
                      { value: "light", label: "Light" },
                      { value: "system", label: "Auto" },
                      { value: "dark", label: "Dark" },
                    ]}
                  />
                </SettingRow>
                <SettingRow
                  title="Accent color"
                  sub={`Live preview · ${ACCENT_LABEL[accent]}. Used for primary actions and selection.`}
                >
                  <div className="flex items-center gap-3">
                    {ACCENTS.map((a) => (
                      <button
                        key={a}
                        type="button"
                        aria-label={ACCENT_LABEL[a]}
                        aria-pressed={accent === a}
                        onClick={() => setAccent(a)}
                        style={{ background: ACCENT_SWATCH[a] }}
                        className={
                          "h-8 w-8 rounded-full border-[3px] transition-transform duration-150 ease-out " +
                          (accent === a
                            ? "border-text scale-[1.08]"
                            : "border-transparent hover:scale-105")
                        }
                      />
                    ))}
                  </div>
                </SettingRow>
                <SettingRow
                  title="Density"
                  sub="Compact tightens set-row spacing during workouts"
                >
                  <SegControl
                    aria-label="Density"
                    value={prefs.density}
                    onChange={(v) => prefs.setPref("density", v)}
                    options={[
                      { value: "regular", label: "Regular" },
                      { value: "compact", label: "Compact" },
                    ]}
                  />
                </SettingRow>
              </Card>
            </Section>
          </RevealItem>

          {/* Units */}
          <RevealItem>
            <Section
              id="units"
              title="Units & defaults"
              sub="Stored as kg and meters under the hood — display only."
            >
              <Card>
                <SettingRow title="Weight">
                  <SegControl
                    aria-label="Weight unit"
                    value={me.unit_system === "imperial" ? "lb" : "kg"}
                    disabled={updateMe.isPending}
                    onChange={(v) =>
                      patchMe({ unit_system: v === "lb" ? "imperial" : "metric" }, "Weight unit")
                    }
                    options={[
                      { value: "kg", label: "kg" },
                      { value: "lb", label: "lb" },
                    ]}
                  />
                </SettingRow>
                <SettingRow title="Distance">
                  <SegControl
                    aria-label="Distance unit"
                    value={prefs.distance}
                    onChange={(v) => prefs.setPref("distance", v)}
                    options={[
                      { value: "km", label: "km" },
                      { value: "mi", label: "mi" },
                    ]}
                  />
                </SettingRow>
              </Card>
            </Section>
          </RevealItem>

          {/* Training */}
          <RevealItem>
            <Section
              id="training"
              title="Active program"
              sub="The active program drives your scheduled sessions. Activating sets a start date, so switch from a program's page."
            >
              <Card>
                <SettingRow
                  title="Active program"
                  sub={
                    activeProgram
                      ? `Activated ${relativeTime(activeProgram.activated_at)}`
                      : "No program is active"
                  }
                >
                  {activeProgram ? (
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/programs/${activeProgram.id}`}
                        className="text-accent text-sm font-medium hover:underline"
                      >
                        {activeProgram.name}
                      </Link>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={deactivate.isPending}
                        onClick={() =>
                          deactivate.mutate(activeProgram.id, {
                            onSuccess: () => {
                              programsQuery.refetch();
                              pushToast({ kind: "success", message: "Program deactivated" });
                            },
                            onError: (e) =>
                              pushToast({
                                kind: "error",
                                message: (e as unknown as ApiError)?.message ?? "Failed",
                              }),
                          })
                        }
                      >
                        {deactivate.isPending ? "…" : "Deactivate"}
                      </Button>
                    </div>
                  ) : (
                    <Link
                      href="/programs"
                      className="text-accent text-sm font-medium hover:underline"
                    >
                      Browse programs
                    </Link>
                  )}
                </SettingRow>
                {inactivePrograms.length > 0 ? (
                  <SettingRow
                    title="Switch program"
                    sub="Open a program to activate it with a start date"
                  >
                    <select
                      aria-label="Switch program"
                      className="bg-surface text-text border-border focus:border-accent focus:ring-accent-soft h-[34px] rounded-[var(--radius-button)] border px-3 text-sm transition-[border-color,box-shadow] duration-150 ease-out focus:ring-[3px] focus:outline-none"
                      value=""
                      onChange={(e) => {
                        if (e.target.value) router.push(`/programs/${e.target.value}`);
                      }}
                    >
                      <option value="">Choose…</option>
                      {inactivePrograms.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </SettingRow>
                ) : null}
                <SettingRow
                  title="Default rest timer"
                  sub="Used to pre-fill the rest timer during workouts"
                >
                  <Input
                    className="h-[34px] w-[100px] text-center"
                    value={restDraft}
                    onChange={(e) => setRestDraft(e.target.value)}
                    onBlur={commitRest}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                    }}
                  />
                </SettingRow>
              </Card>
            </Section>
          </RevealItem>

          {/* Nutrition */}
          <RevealItem>
            <Section
              id="nutrition"
              title="Tracking mode"
              sub="Flexible logs meals freely; Plan logs against an active meal plan's slots. Switching is non-destructive — today's meals carry over."
            >
              <Card>
                <SettingRow
                  title="How you track nutrition"
                  sub="Switching to Plan uses your active meal plan's meals and targets"
                >
                  <SegControl
                    aria-label="Nutrition tracking mode"
                    value={me.nutrition_mode ?? "flexible"}
                    disabled={updateMe.isPending}
                    onChange={(v) => patchMe({ nutrition_mode: v }, "Tracking mode")}
                    options={[
                      { value: "flexible", label: "Flexible" },
                      { value: "plan", label: "Plan" },
                    ]}
                  />
                </SettingRow>
              </Card>
            </Section>
          </RevealItem>

          {/* Connections — defers to Health for the wearable connection (page spec 04). */}
          <RevealItem>
            <Section
              id="connections"
              title="Connected services"
              sub="Your wearable connection lives on Health, alongside the data it syncs. Manage it there."
            >
              <Link
                href="/health"
                className="border-border bg-surface-elevated hover:border-border-strong grid grid-cols-[44px_1fr_auto] items-center gap-4 rounded-[var(--radius-card)] border p-[18px] transition-colors"
              >
                <div className="bg-surface text-text-secondary grid h-11 w-11 place-items-center rounded-[10px]">
                  <Activity className="h-[22px] w-[22px]" strokeWidth={1.6} />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-semibold">Wearable (Fitbit via Google)</div>
                  <div
                    className={
                      health?.needs_reauth
                        ? "text-destructive mt-0.5 text-xs"
                        : "text-text-tertiary mt-0.5 text-xs"
                    }
                  >
                    {healthStatus} · manage on Health
                  </div>
                </div>
                <ArrowRight className="text-text-tertiary h-[18px] w-[18px]" aria-hidden />
              </Link>
            </Section>
          </RevealItem>

          {/* Data */}
          <RevealItem>
            <Section
              id="data"
              title="Data"
              sub="Your data lives in your account. Export it as CSV anytime."
            >
              <Card>
                <SettingRow title="Export workouts" sub="CSV · last 12 months">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      pushToast({
                        kind: "info",
                        message: "Export endpoint not available yet (API-14)",
                      })
                    }
                  >
                    Download
                  </Button>
                </SettingRow>
                <SettingRow title="Export nutrition" sub="CSV · last 12 months">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      pushToast({
                        kind: "info",
                        message: "Export endpoint not available yet (API-14)",
                      })
                    }
                  >
                    Download
                  </Button>
                </SettingRow>
                <SettingRow
                  title="Delete account"
                  sub="Permanent. 7-day grace period before purge."
                  destructive
                >
                  <Button variant="destructive" size="sm" onClick={() => setConfirmDelete(true)}>
                    Delete
                  </Button>
                </SettingRow>
              </Card>
            </Section>
          </RevealItem>

          <RevealItem>
            <section id="about" className="scroll-mt-[88px]">
              <h3 className="mb-1 text-lg font-semibold tracking-[-0.01em]">About</h3>
              <Link
                href="/help"
                className="border-border bg-surface-elevated hover:border-border-strong mt-2 mb-4 flex items-center justify-between rounded-[var(--radius-card)] border px-4 py-3 transition-colors"
              >
                <span>
                  <span className="text-text block text-sm font-semibold">Help &amp; how-to</span>
                  <span className="text-text-secondary block text-[13px]">
                    Guides for every screen, plus replay the welcome tour.
                  </span>
                </span>
                <ArrowRight className="text-text-tertiary h-[18px] w-[18px]" aria-hidden />
              </Link>
              <p className="text-text-secondary mb-4 text-[13px]">Version 0.32.1</p>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => signOut.mutate()}
                disabled={signOut.isPending}
              >
                {signOut.isPending ? "Signing out…" : "Sign out"}
              </Button>
            </section>
          </RevealItem>
        </RevealGroup>
      </div>

      <Sheet open={confirmDelete} onOpenChange={setConfirmDelete} title="Delete account?">
        <p className="text-text-secondary text-sm">
          This permanently deletes your account and all training and nutrition data. There is a
          7-day grace period before data is purged. This action cannot be undone here.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Button
            variant="ghost"
            onClick={() => setConfirmDelete(false)}
            disabled={deleteAccount.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={deleteAccount.isPending}
            onClick={() =>
              deleteAccount.mutate(undefined, {
                onSuccess: async () => {
                  // Clear the local httpOnly auth cookies, then bounce to sign-in.
                  await fetch("/api/auth/logout", {
                    method: "POST",
                    credentials: "include",
                  }).catch(() => undefined);
                  qc.clear();
                  setConfirmDelete(false);
                  router.push("/sign-in");
                },
                onError: (e) =>
                  pushToast({
                    kind: "error",
                    message: `Couldn't delete account: ${(e as unknown as ApiError)?.message ?? ""}`,
                  }),
              })
            }
          >
            {deleteAccount.isPending ? "Deleting…" : "Delete account"}
          </Button>
        </div>
      </Sheet>
    </div>
  );
}

function Section({
  id,
  title,
  sub,
  children,
}: {
  id: string;
  title: string;
  sub: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-[88px]">
      <h3 className="mb-1 text-lg font-semibold tracking-[-0.01em]">{title}</h3>
      <p className="text-text-secondary mb-4 text-[13px]">{sub}</p>
      {children}
    </section>
  );
}
