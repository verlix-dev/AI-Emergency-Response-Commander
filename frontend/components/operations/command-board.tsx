"use client";

import { motion } from "framer-motion";
import { RotateCcw, X } from "lucide-react";

import { DecisionPanel } from "@/components/operations/decision-panel";
import { ReadinessBoard } from "@/components/operations/readiness-board";
import { ResponsePanel } from "@/components/operations/response-panel";
import { ScenePanel } from "@/components/operations/scene-panel";
import { Badge } from "@/components/ui/badge";
import { formatDateTime } from "@/lib/format";
import { useUiStore } from "@/stores/use-ui-store";

/**
 * The active command board.
 *
 * Three columns matching the operational reading order: what was seen, what it means, what to do.
 * Falls back to the readiness board when no analysis is loaded.
 */
export function CommandBoard() {
  const { activeAnalysis, activeImageUrl, clearActiveAnalysis, setAnalyzeOpen } = useUiStore();

  if (!activeAnalysis) return <ReadinessBoard />;

  const { incident, decision, resources, commander_brief, scene, timestamp } = activeAnalysis;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="space-y-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-card px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-sm font-semibold text-slate-100">{incident.title}</h2>
            <Badge>{incident.status}</Badge>
          </div>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            Analysed {formatDateTime(timestamp)} · Incident{" "}
            <span className="font-mono">{incident.id.slice(0, 8)}</span>
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => setAnalyzeOpen(true)}
            className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <RotateCcw aria-hidden size={12} />
            New Analysis
          </button>
          <button
            type="button"
            onClick={clearActiveAnalysis}
            aria-label="Clear active analysis"
            className="rounded border p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <X aria-hidden size={13} />
          </button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <ScenePanel imageUrl={activeImageUrl} scene={scene} />
        <DecisionPanel decision={decision} incident={incident} />
        <ResponsePanel brief={commander_brief} resources={resources} />
      </div>
    </motion.div>
  );
}
