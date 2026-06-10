"use client";

import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Sheet } from "@/components/ui/sheet";
import type { DeleteScope } from "@/lib/api/nutrition";

interface Props {
  open: boolean;
  onClose: () => void;
  mealName: string;
  /** Whether this meal came from the plan (enables the "forever" choice). */
  fromPlan: boolean;
  onDelete: (scope: DeleteScope) => Promise<void> | void;
  pending?: boolean;
}

/**
 * Confirm a meal delete. For plan-backed meals the user chooses "just today"
 * (remove today's log only) or "forever" (also drop it from the plan template).
 */
export function DeleteMealSheet({ open, onClose, mealName, fromPlan, onDelete, pending }: Props) {
  return (
    <Sheet open={open} onOpenChange={(v) => (v ? null : onClose())} title="Delete meal">
      <div className="flex flex-col gap-4">
        <p className="text-text-secondary text-sm">
          {fromPlan
            ? `Remove "${mealName}" just for today, or forever from the plan?`
            : `Delete "${mealName}"? This cannot be undone.`}
        </p>

        {fromPlan ? (
          <div className="flex flex-col gap-2">
            <Button
              variant="secondary"
              disabled={pending}
              onClick={() => onDelete("today")}
              className="justify-start"
            >
              {pending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" aria-hidden /> : null}
              Just today
              <span className="text-text-tertiary ml-1 text-[11px] font-normal">
                keeps it on future days
              </span>
            </Button>
            <Button
              variant="destructive"
              disabled={pending}
              onClick={() => onDelete("forever")}
              className="justify-start"
            >
              {pending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" aria-hidden /> : null}
              Forever
              <span className="ml-1 text-[11px] font-normal opacity-80">
                removes it from the plan
              </span>
            </Button>
          </div>
        ) : (
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={onClose} disabled={pending}>
              Cancel
            </Button>
            <Button variant="destructive" size="sm" disabled={pending} onClick={() => onDelete("today")}>
              {pending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" aria-hidden /> : null}
              Delete
            </Button>
          </div>
        )}
      </div>
    </Sheet>
  );
}
