import type { HTMLAttributes } from "react";

import type { ToneClasses } from "@/lib/display";
import { NEUTRAL_TONE } from "@/lib/display";
import { cn } from "@/lib/utils";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: ToneClasses;
}

export function Badge({ className, tone = NEUTRAL_TONE, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide",
        tone.border,
        tone.background,
        tone.text,
        className,
      )}
      {...props}
    />
  );
}

export function StatusDot({ tone, className }: { tone: ToneClasses; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn("inline-block size-2 shrink-0 rounded-full", tone.dot, className)}
    />
  );
}
