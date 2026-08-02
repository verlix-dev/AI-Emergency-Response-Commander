"use client";

import { motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";

import { Badge, StatusDot } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelBody } from "@/components/ui/card";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { STATUS_TONE } from "@/lib/display";
import { useSystemStatus } from "@/lib/queries";
import { useUiStore } from "@/stores/use-ui-store";

/**
 * The idle command board.
 *
 * Shown when no analysis is loaded. Readiness comes from the backend's own subsystem probe, so a
 * degraded component is reported honestly rather than shown uniformly green.
 */
export function ReadinessBoard() {
  const { data, isPending, isError, error, refetch } = useSystemStatus();
  const setAnalyzeOpen = useUiStore((state) => state.setAnalyzeOpen);

  const allReady = data?.status === "OPERATIONAL";

  return (
    <Panel className="flex min-h-[26rem] items-center justify-center">
      <PanelBody className="w-full max-w-2xl text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
        >
          <div className="mx-auto mb-5 flex size-14 items-center justify-center rounded-full border border-emerald-900 bg-emerald-950/40 text-emerald-400">
            <ShieldCheck aria-hidden size={26} />
          </div>

          <h2 className="text-2xl font-semibold tracking-tight text-slate-50">
            No Active Emergency
          </h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            {allReady
              ? "All subsystems report ready. Submit scene imagery to begin an incident analysis."
              : "Review subsystem readiness below before committing to an analysis."}
          </p>

          <div className="mt-7">
            {isPending ? (
              <LoadingState label="Checking system readiness…" className="py-4" />
            ) : isError ? (
              <ErrorState error={error} onRetry={() => void refetch()} className="py-4" />
            ) : (
              <ul className="mx-auto grid max-w-xl gap-2 sm:grid-cols-2">
                {data.components.map((component, index) => {
                  const tone = STATUS_TONE[component.status];
                  return (
                    <motion.li
                      key={component.component}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.1 + index * 0.06, duration: 0.25 }}
                      className="flex items-center justify-between gap-3 rounded border bg-slate-900/40 px-3 py-2 text-left"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-xs font-medium text-slate-100">
                          {component.label}
                        </span>
                        <span className="block truncate text-[10px] text-muted-foreground">
                          {component.detail}
                        </span>
                      </span>
                      <Badge tone={tone} className="shrink-0">
                        <StatusDot
                          tone={tone}
                          className={component.status === "OPERATIONAL" ? "animate-pulse" : ""}
                        />
                        {component.status === "OPERATIONAL" ? "Ready" : component.status}
                      </Badge>
                    </motion.li>
                  );
                })}
              </ul>
            )}
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.45, duration: 0.3 }}
            className="mt-8"
          >
            <Button onClick={() => setAnalyzeOpen(true)} className="px-6">
              Analyze New Incident
            </Button>
          </motion.div>
        </motion.div>
      </PanelBody>
    </Panel>
  );
}
