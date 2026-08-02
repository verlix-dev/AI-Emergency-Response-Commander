"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Radio } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { PRIORITY_TONE, RESOURCE_LABEL, SEVERITY_TONE, disasterLabel } from "@/lib/display";
import { formatDateTime, formatRelative, formatConfidence } from "@/lib/format";
import { useIncidentTimeline, useIncidents } from "@/lib/queries";
import type { IncidentSummary, PriorityLevel, SeverityLevel } from "@/lib/types";
import { useUiStore } from "@/stores/use-ui-store";

/** The detail body for an expanded incident, loaded from the timeline endpoint on demand. */
function IncidentDetail({ incidentId }: { incidentId: string }) {
  const { data, isPending, isError, error, refetch } = useIncidentTimeline(incidentId);

  if (isPending) return <LoadingState label="Loading incident record…" className="py-6" />;
  if (isError) return <ErrorState error={error} onRetry={() => void refetch()} className="py-6" />;

  const latest = data.revisions.at(-1);
  if (!latest) {
    return (
      <p className="px-4 pb-4 text-xs text-muted-foreground">
        This incident has no recorded analysis.
      </p>
    );
  }

  const brief = latest.commander_brief;

  return (
    <div className="space-y-4 border-t bg-slate-950/40 px-4 py-4">
      <div>
        <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Commander Brief
        </p>
        <p className="text-xs leading-relaxed text-slate-300">{brief.incident_summary}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            Immediate Actions
          </p>
          <ol className="space-y-1">
            {brief.immediate_actions.slice(0, 5).map((action, index) => (
              <li key={action} className="flex gap-2 text-[11px] text-slate-300">
                <span className="font-mono text-cyan-400">{index + 1}.</span>
                {action}
              </li>
            ))}
          </ol>
        </div>

        <div>
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            Resources
          </p>
          {latest.resources.recommendations.length === 0 ? (
            <p className="text-[11px] text-muted-foreground">No requirements derived.</p>
          ) : (
            <ul className="space-y-1">
              {latest.resources.recommendations.map((item) => (
                <li
                  key={item.resource_kind}
                  className="flex justify-between gap-2 text-[11px] text-slate-300"
                >
                  <span>
                    {item.quantity}× {RESOURCE_LABEL[item.resource_kind]}
                  </span>
                  {item.shortfall > 0 ? (
                    <span className="text-red-300">{item.shortfall} short</span>
                  ) : (
                    <span className="text-emerald-300">assigned</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {data.revisions.length > 1 ? (
        <div>
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            Analysis History · {data.revisions.length} revisions
          </p>
          <ol className="space-y-1">
            {data.revisions.map((revision) => (
              <li
                key={revision.id}
                className="flex items-center justify-between gap-2 text-[11px] text-slate-400"
              >
                <span className="font-mono">Rev {revision.revision}</span>
                <span>{revision.severity_level}</span>
                <span>{formatDateTime(revision.created_at)}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      <p className="border-t pt-2.5 text-[11px] text-muted-foreground">
        Analysed {formatDateTime(latest.created_at)} · Confidence{" "}
        {formatConfidence(latest.confidence)}
      </p>
    </div>
  );
}

function IncidentRow({ incident, index }: { incident: IncidentSummary; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const severityTone = incident.severity_level
    ? SEVERITY_TONE[incident.severity_level as SeverityLevel]
    : undefined;
  const priorityTone = PRIORITY_TONE[incident.priority as PriorityLevel];

  return (
    <motion.li
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.04, 0.3), duration: 0.25 }}
      className="overflow-hidden rounded-md border bg-slate-900/30"
    >
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-900/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cyan-400"
      >
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-100">{incident.title}</p>
          <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
            {disasterLabel(incident.incident_type)} · {incident.location} ·{" "}
            {formatRelative(incident.created_at)}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {severityTone ? <Badge tone={severityTone}>{incident.severity_level}</Badge> : null}
          {priorityTone ? <Badge tone={priorityTone}>{incident.priority}</Badge> : null}
          <ChevronDown
            aria-hidden
            size={15}
            className={`text-muted-foreground transition-transform ${expanded ? "rotate-180" : ""}`}
          />
        </div>
      </button>

      <AnimatePresence initial={false}>
        {expanded ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <IncidentDetail incidentId={incident.id} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </motion.li>
  );
}

export function OperationsFeed() {
  const { data, isPending, isError, error, refetch } = useIncidents();
  const setAnalyzeOpen = useUiStore((state) => state.setAnalyzeOpen);

  return (
    <Panel>
      <PanelHeader>
        <PanelTitle>Operations Feed</PanelTitle>
        {data ? (
          <span className="text-[11px] text-muted-foreground">
            {data.total} recorded {data.total === 1 ? "incident" : "incidents"}
          </span>
        ) : null}
      </PanelHeader>

      <PanelBody>
        {isPending ? (
          <LoadingState label="Loading operations feed…" />
        ) : isError ? (
          <ErrorState error={error} onRetry={() => void refetch()} />
        ) : data.incidents.length === 0 ? (
          <EmptyState
            icon={<Radio aria-hidden size={26} />}
            title="No incidents on record"
            description="Analysed incidents appear here newest first, with their grading, brief, and resource commitment."
            action={
              <button
                type="button"
                onClick={() => setAnalyzeOpen(true)}
                className="rounded bg-cyan-400 px-3 py-1.5 text-xs font-medium text-slate-950 transition-colors hover:bg-cyan-300"
              >
                Analyze New Incident
              </button>
            }
          />
        ) : (
          <ul className="space-y-2">
            {data.incidents.map((incident, index) => (
              <IncidentRow key={incident.id} incident={incident} index={index} />
            ))}
          </ul>
        )}
      </PanelBody>
    </Panel>
  );
}
