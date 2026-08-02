"use client";

import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * The reasoning stages the backend runs, in order.
 *
 * The backend performs analysis in a single synchronous request, so it does not stream stage
 * events. Progress therefore advances on elapsed time as an honest indication of which stage is
 * expected to be running — never as a claim that a stage has returned. The final stage only
 * settles when the request itself resolves, so the display can never report completion the
 * backend has not confirmed.
 */
export const PIPELINE_STAGES = [
  { id: "vision", label: "Vision Analysis", detail: "Reading the submitted imagery" },
  { id: "detection", label: "Object Detection", detail: "Identifying people, hazards, and assets" },
  { id: "situation", label: "Situation Assessment", detail: "Building the structured assessment" },
  { id: "decision", label: "Decision Intelligence", detail: "Grading severity, urgency, confidence" },
  { id: "allocation", label: "Resource Allocation", detail: "Matching requirements to available units" },
  { id: "brief", label: "Commander Brief", detail: "Composing the operational briefing" },
] as const;

export type PipelinePhase = "pending" | "active" | "complete";

function StageRow({
  label,
  detail,
  phase,
  index,
}: {
  label: string;
  detail: string;
  phase: PipelinePhase;
  index: number;
}) {
  return (
    <motion.li
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05, duration: 0.25 }}
      className="flex items-start gap-3"
    >
      <div
        className={cn(
          "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors",
          phase === "complete" && "border-emerald-500/60 bg-emerald-500/15 text-emerald-300",
          phase === "active" && "border-cyan-400/60 bg-cyan-400/15 text-cyan-300",
          phase === "pending" && "border-slate-700 text-slate-600",
        )}
      >
        {phase === "complete" ? (
          <Check aria-hidden size={12} strokeWidth={3} />
        ) : phase === "active" ? (
          <Loader2 aria-hidden size={12} className="animate-spin" />
        ) : (
          <span className="size-1.5 rounded-full bg-current" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "text-sm font-medium transition-colors",
            phase === "pending" ? "text-slate-500" : "text-slate-100",
          )}
        >
          {label}
        </p>
        <p className="truncate text-xs text-muted-foreground">{detail}</p>
      </div>

      {phase === "active" ? (
        <span className="mt-0.5 shrink-0 text-[10px] font-semibold uppercase tracking-wider text-cyan-300">
          Running
        </span>
      ) : null}
    </motion.li>
  );
}

export function PipelineProgress({ activeIndex }: { activeIndex: number }) {
  const completed = Math.max(0, Math.min(activeIndex, PIPELINE_STAGES.length));
  const percent = Math.round((completed / PIPELINE_STAGES.length) * 100);

  return (
    <div>
      <div className="mb-4 h-1 overflow-hidden rounded-full bg-slate-800">
        <motion.div
          className="h-full bg-cyan-400"
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>

      <ul className="space-y-3.5" aria-live="polite">
        {PIPELINE_STAGES.map((stage, index) => (
          <StageRow
            key={stage.id}
            label={stage.label}
            detail={stage.detail}
            index={index}
            phase={
              index < activeIndex ? "complete" : index === activeIndex ? "active" : "pending"
            }
          />
        ))}
      </ul>
    </div>
  );
}
