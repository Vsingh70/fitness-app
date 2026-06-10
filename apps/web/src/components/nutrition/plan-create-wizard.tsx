"use client";

import { ChevronLeft } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/ui/sheet";
import {
  CONTENT_MODE_LABEL,
  DOW_LABEL,
  PLAN_KIND_LABEL,
  TRACKING_MODE_LABEL,
  dayRolesForKind,
  type ContentMode,
  type MealPlanCreate,
  type MealPlanDayCreate,
  type PlanKind,
  type TrackingMode,
} from "@/lib/api/meal-plans";
import { useMyPrograms } from "@/lib/hooks/programs";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreate: (body: MealPlanCreate) => void;
  pending: boolean;
}

type Step = "name" | "kind" | "content" | "tracking" | "training" | "weekly";

const PLAN_KINDS: PlanKind[] = ["daily_repeating", "training_rest", "weekly"];
const CONTENT_MODES: ContentMode[] = ["targets_only", "meals_only", "targets_and_meals"];
const TRACKING_MODES: TrackingMode[] = ["calories_only", "macros_only", "macros_and_calories"];

const KIND_HELP: Record<PlanKind, string> = {
  daily_repeating: "One day template that applies to every date.",
  training_rest: "Separate training-day and rest-day templates.",
  weekly: "Seven templates, one per weekday, that can reset each week.",
};

const CONTENT_HELP: Record<ContentMode, string> = {
  targets_only: "Just set numbers and track against them.",
  meals_only: "Plan meals; day targets come from the summed foods.",
  targets_and_meals: "Plan meals and set explicit targets.",
};

const TRACKING_HELP: Record<TrackingMode, string> = {
  calories_only: "Rings and bars track calories only.",
  macros_only: "Track protein, carbs, and fat.",
  macros_and_calories: "Track both macros and calories.",
};

export function PlanCreateWizard({ open, onClose, onCreate, pending }: Props) {
  const programs = useMyPrograms();
  const activeProgram = programs.data?.items.find((p) => p.is_active) ?? null;

  const [step, setStep] = useState<Step>("name");
  const [name, setName] = useState("");
  const [kind, setKind] = useState<PlanKind>("daily_repeating");
  const [content, setContent] = useState<ContentMode>("targets_and_meals");
  const [tracking, setTracking] = useState<TrackingMode>("macros_and_calories");

  // training_rest
  const [syncProgram, setSyncProgram] = useState(false);
  const [trainingDows, setTrainingDows] = useState<number[]>([1, 3, 5]);

  // weekly
  const [weekResets, setWeekResets] = useState(false);
  const [weekStartDow, setWeekStartDow] = useState(1);

  const reset = () => {
    setStep("name");
    setName("");
    setKind("daily_repeating");
    setContent("targets_and_meals");
    setTracking("macros_and_calories");
    setSyncProgram(false);
    setTrainingDows([1, 3, 5]);
    setWeekResets(false);
    setWeekStartDow(1);
  };

  const close = () => {
    reset();
    onClose();
  };

  // The step sequence depends on plan kind.
  const steps = useMemo<Step[]>(() => {
    const base: Step[] = ["name", "kind", "content", "tracking"];
    if (kind === "training_rest") base.push("training");
    if (kind === "weekly") base.push("weekly");
    return base;
  }, [kind]);

  const idx = steps.indexOf(step);
  const isLast = idx === steps.length - 1;
  const next = () => {
    if (isLast) return submit();
    setStep(steps[idx + 1]!);
  };
  const back = () => {
    if (idx > 0) setStep(steps[idx - 1]!);
  };

  const toggleDow = (dow: number) =>
    setTrainingDows((prev) =>
      prev.includes(dow) ? prev.filter((d) => d !== dow) : [...prev, dow].sort((a, b) => a - b),
    );

  const submit = () => {
    if (!name.trim()) return;
    // Seed empty day templates so the editor has somewhere to add meals.
    const dayTemplates: MealPlanDayCreate[] = dayRolesForKind(kind).map((role) => ({
      day_role: role,
    }));
    onCreate({
      name: name.trim(),
      plan_kind: kind,
      content_mode: content,
      tracking_mode: tracking,
      synced_to_program: kind === "training_rest" ? syncProgram : false,
      training_dows: kind === "training_rest" && !syncProgram ? trainingDows : [],
      week_resets: kind === "weekly" ? weekResets : false,
      week_start_dow: kind === "weekly" ? weekStartDow : 0,
      day_templates: dayTemplates,
    });
  };

  const canAdvance =
    step === "name" ? name.trim().length > 0 : !(step === "training" && syncProgram && !activeProgram);

  return (
    <Sheet open={open} onOpenChange={(v) => (v ? null : close())} title="New meal plan">
      <div className="flex flex-col gap-5">
        {/* Progress */}
        <div className="flex gap-1.5">
          {steps.map((s, i) => (
            <span
              key={s}
              className={
                "h-1 flex-1 rounded-full " + (i <= idx ? "bg-accent" : "bg-border-strong")
              }
            />
          ))}
        </div>

        {step === "name" ? (
          <label className="flex flex-col gap-1.5">
            <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
              Plan name
            </span>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Lean bulk"
              autoFocus
            />
          </label>
        ) : null}

        {step === "kind" ? (
          <ChoiceList
            label="Plan kind"
            options={PLAN_KINDS}
            value={kind}
            optionLabel={(k) => PLAN_KIND_LABEL[k]}
            optionHelp={(k) => KIND_HELP[k]}
            onSelect={setKind}
          />
        ) : null}

        {step === "content" ? (
          <ChoiceList
            label="What does the plan carry?"
            options={CONTENT_MODES}
            value={content}
            optionLabel={(m) => CONTENT_MODE_LABEL[m]}
            optionHelp={(m) => CONTENT_HELP[m]}
            onSelect={setContent}
          />
        ) : null}

        {step === "tracking" ? (
          <ChoiceList
            label="What do you track against?"
            options={TRACKING_MODES}
            value={tracking}
            optionLabel={(m) => TRACKING_MODE_LABEL[m]}
            optionHelp={(m) => TRACKING_HELP[m]}
            onSelect={setTracking}
          />
        ) : null}

        {step === "training" ? (
          <div className="flex flex-col gap-3">
            <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
              Map training vs rest days
            </span>
            <OptionRow
              selected={!syncProgram}
              title="Set weekdays by hand"
              help="Pick which weekdays are training days; the rest are rest days."
              onSelect={() => setSyncProgram(false)}
            />
            <OptionRow
              selected={syncProgram}
              title="Sync to active program"
              help={
                activeProgram
                  ? `Workout days from "${activeProgram.name}" use the training template.`
                  : "No active program yet. Activate a program first to use this."
              }
              disabled={!activeProgram}
              onSelect={() => activeProgram && setSyncProgram(true)}
            />
            {!syncProgram ? (
              <div className="flex flex-wrap gap-1.5">
                {DOW_LABEL.map((label, dow) => (
                  <button
                    key={dow}
                    type="button"
                    onClick={() => toggleDow(dow)}
                    className={
                      "rounded-[var(--radius-pill)] border px-3 py-1 text-xs font-medium transition-colors " +
                      (trainingDows.includes(dow)
                        ? "border-accent bg-accent-soft text-accent"
                        : "border-border text-text-secondary hover:border-border-strong")
                    }
                  >
                    {label.slice(0, 3)}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {step === "weekly" ? (
          <div className="flex flex-col gap-3">
            <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
              Weekly reset
            </span>
            <label className="text-text-secondary flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={weekResets}
                onChange={(e) => setWeekResets(e.target.checked)}
              />
              Prompt me to review targets at the start of each week
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
                Week starts on
              </span>
              <select
                value={weekStartDow}
                onChange={(e) => setWeekStartDow(Number(e.target.value))}
                className="border-border-strong bg-surface-elevated text-text h-[42px] w-full rounded-[var(--radius-button)] border px-3 text-sm"
              >
                {DOW_LABEL.map((label, dow) => (
                  <option key={dow} value={dow}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        ) : null}

        {/* Nav */}
        <div className="mt-1 flex items-center justify-between gap-2">
          {idx > 0 ? (
            <Button variant="ghost" size="sm" onClick={back} disabled={pending}>
              <ChevronLeft className="mr-1 h-4 w-4" aria-hidden /> Back
            </Button>
          ) : (
            <Button variant="ghost" size="sm" onClick={close} disabled={pending}>
              Cancel
            </Button>
          )}
          <Button size="sm" onClick={next} disabled={!canAdvance || pending}>
            {isLast ? (pending ? "Creating…" : "Create plan") : "Continue"}
          </Button>
        </div>
      </div>
    </Sheet>
  );
}

function ChoiceList<T extends string>({
  label,
  options,
  value,
  optionLabel,
  optionHelp,
  onSelect,
}: {
  label: string;
  options: readonly T[];
  value: T;
  optionLabel: (o: T) => string;
  optionHelp: (o: T) => string;
  onSelect: (o: T) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <span className="text-text-tertiary text-[11px] font-semibold tracking-[0.08em] uppercase">
        {label}
      </span>
      {options.map((o) => (
        <OptionRow
          key={o}
          selected={value === o}
          title={optionLabel(o)}
          help={optionHelp(o)}
          onSelect={() => onSelect(o)}
        />
      ))}
    </div>
  );
}

function OptionRow({
  selected,
  title,
  help,
  disabled,
  onSelect,
}: {
  selected: boolean;
  title: string;
  help: string;
  disabled?: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onSelect}
      className={
        "rounded-[var(--radius-card)] border p-3 text-left transition-colors " +
        (disabled ? "opacity-50 " : "") +
        (selected
          ? "border-accent bg-accent-soft"
          : "border-border hover:border-border-strong")
      }
    >
      <span className={"block text-sm font-semibold " + (selected ? "text-accent" : "text-text")}>
        {title}
      </span>
      <span className="text-text-secondary mt-0.5 block text-xs">{help}</span>
    </button>
  );
}
