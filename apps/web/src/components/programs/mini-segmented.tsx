"use client";

/**
 * Compact ink-filled segmented control — the design's `.mini-seg`. Used for the
 * per-exercise Range/Target rep toggle and the program-wide RPE/RIR/Off intensity
 * control. The active segment fills with text ink; inactive segments stay quiet.
 * Styled by programs.css (.mini-seg), not Tailwind, so it matches the prototype
 * exactly. (Distinct from the app-wide `components/ui/segmented.tsx`.)
 */
export function MiniSegmented<T extends string>({
  options,
  value,
  onChange,
  disabled,
  ariaLabel,
}: {
  options: readonly { value: T; label: string }[];
  value: T;
  onChange?: (value: T) => void;
  disabled?: boolean;
  ariaLabel?: string;
}) {
  return (
    <div className="mini-seg" role="radiogroup" aria-label={ariaLabel}>
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="radio"
          aria-checked={opt.value === value}
          disabled={disabled}
          onClick={() => onChange?.(opt.value)}
          className={`ms ${opt.value === value ? "on" : ""}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
