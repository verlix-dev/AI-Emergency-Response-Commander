"use client";

import { motion } from "framer-motion";
import { Cpu, Database, Network, Radar, Truck } from "lucide-react";
import type { ReactNode } from "react";

import { Badge, StatusDot } from "@/components/ui/badge";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/components/ui/card";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { STATUS_TONE } from "@/lib/display";
import { formatDateTime } from "@/lib/format";
import { useSystemStatus } from "@/lib/queries";
import { API_BASE_URL } from "@/lib/api";

const COMPONENT_ICONS: Record<string, ReactNode> = {
  vision: <Radar aria-hidden size={15} />,
  decision: <Cpu aria-hidden size={15} />,
  database: <Database aria-hidden size={15} />,
  resources: <Truck aria-hidden size={15} />,
  api: <Network aria-hidden size={15} />,
};

export function SystemStatusView() {
  const { data, isPending, isError, error, refetch } = useSystemStatus();

  if (isPending) return <LoadingState label="Probing subsystems…" />;
  if (isError) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const overallTone = STATUS_TONE[data.status];

  return (
    <Panel>
      <PanelHeader>
        <PanelTitle>System Status</PanelTitle>
        <Badge tone={overallTone}>
          <StatusDot tone={overallTone} />
          {data.status}
        </Badge>
      </PanelHeader>

      <PanelBody>
        <ul className="space-y-2">
          {data.components.map((component, index) => {
            const tone = STATUS_TONE[component.status];
            return (
              <motion.li
                key={component.component}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.05, 0.3), duration: 0.2 }}
                className="flex items-center gap-3 rounded border bg-slate-900/30 px-3 py-2.5"
              >
                <span className={`shrink-0 ${tone.text}`}>
                  {COMPONENT_ICONS[component.component] ?? <Cpu aria-hidden size={15} />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-xs font-medium text-slate-100">
                    {component.label}
                  </span>
                  <span className="block truncate text-[11px] text-muted-foreground">
                    {component.detail}
                  </span>
                </span>
                <Badge tone={tone} className="shrink-0">
                  <StatusDot tone={tone} />
                  {component.status}
                </Badge>
              </motion.li>
            );
          })}
        </ul>

        <dl className="mt-4 grid grid-cols-2 gap-3 border-t pt-3 text-[11px] sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground">Version</dt>
            <dd className="mt-0.5 font-mono text-slate-200">{data.version}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Environment</dt>
            <dd className="mt-0.5 font-mono text-slate-200">{data.environment}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Endpoint</dt>
            <dd className="mt-0.5 truncate font-mono text-slate-200">{API_BASE_URL}</dd>
          </div>
          <div className="col-span-2 sm:col-span-3">
            <dt className="text-muted-foreground">Last checked</dt>
            <dd className="mt-0.5 font-mono text-slate-200">{formatDateTime(data.checked_at)}</dd>
          </div>
        </dl>
      </PanelBody>
    </Panel>
  );
}
