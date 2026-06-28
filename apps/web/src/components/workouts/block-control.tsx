"use client";

import { Layers } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet } from "@/components/motion/Sheet";
import { cn } from "@/lib/cn";
import { BLOCK_KIND_LABEL, type BlockKind } from "@/lib/workouts/types";

interface BlockControlProps {
  kind: BlockKind;
  label: string | null;
  /** Persist a block change for this session exercise. */
  onChange: (next: { block_kind: BlockKind; block_label: string | null }) => void;
  disabled?: boolean;
}

const ORDER: BlockKind[] = ["warmup", "working", "cooldown"];

/**
 * Compact control to move a session exercise into a warm-up / working /
 * cooldown block and optionally label it (06 §3c). Opens a bottom sheet so it
 * stays reachable one-handed and never stacks deeper than one (05 §6).
 */
export function BlockControl({ kind, label, onChange, disabled = false }: BlockControlProps) {
  const [open, setOpen] = useState(false);
  const [draftKind, setDraftKind] = useState<BlockKind>(kind);
  const [draftLabel, setDraftLabel] = useState(label ?? "");

  // Re-seed the draft whenever the sheet opens against current values.
  useEffect(() => {
    if (open) {
      setDraftKind(kind);
      setDraftLabel(label ?? "");
    }
  }, [open, kind, label]);

  const save = () => {
    onChange({
      block_kind: draftKind,
      block_label: draftLabel.trim() === "" ? null : draftLabel.trim(),
    });
    setOpen(false);
  };

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label="Change block"
        aria-haspopup="dialog"
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        <Layers className="h-4 w-4" />
      </Button>

      <Sheet open={open} onClose={() => setOpen(false)} aria-label="Move to block">
        <div className="flex flex-col gap-4">
          <h2 className="text-text font-serif text-lg font-medium">Move to block</h2>

          <div className="flex flex-col gap-2">
            <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.12em] uppercase">
              Block
            </span>
            <div className="flex flex-wrap gap-2">
              {ORDER.map((k) => (
                <button
                  key={k}
                  type="button"
                  aria-pressed={draftKind === k}
                  onClick={() => setDraftKind(k)}
                  className={cn(
                    "inline-flex h-[34px] items-center rounded-[var(--radius-pill)] border px-3 text-[12px] font-semibold tracking-[0.04em] uppercase transition-colors duration-150",
                    draftKind === k
                      ? "bg-accent text-accent-foreground border-transparent"
                      : "border-border text-text-secondary hover:text-text",
                  )}
                >
                  {BLOCK_KIND_LABEL[k]}
                </button>
              ))}
            </div>
            {draftKind !== "working" ? (
              <p className="text-text-tertiary text-xs">
                Logged and visible in history, but never counted toward working volume, PRs, or
                per-muscle analytics.
              </p>
            ) : null}
          </div>

          <label className="flex flex-col gap-2">
            <span className="text-text-tertiary text-[10px] font-semibold tracking-[0.12em] uppercase">
              Label (optional)
            </span>
            <Input
              value={draftLabel}
              onChange={(e) => setDraftLabel(e.target.value)}
              placeholder="e.g. Mobility"
            />
          </label>

          <div className="flex items-center justify-end gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="button" size="sm" onClick={save}>
              Save
            </Button>
          </div>
        </div>
      </Sheet>
    </>
  );
}
