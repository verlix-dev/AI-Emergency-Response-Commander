"use client";

import { motion } from "framer-motion";
import { ClipboardList, Info, ListChecks, TriangleAlert, Truck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/components/ui/card";
import { ALLOCATION_TONE, RESOURCE_LABEL } from "@/lib/display";
import { pluralize } from "@/lib/format";
import type { AllocationResult, CommanderBrief } from "@/lib/types";

function SectionHeading({
  icon,
  children,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <p className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
      {icon}
      {children}
    </p>
  );
}

export function ResponsePanel({
  brief,
  resources,
}: {
  brief: CommanderBrief;
  resources: AllocationResult;
}) {
  const shortfallUnits = resources.total_units_requested - resources.total_units_fulfilled;

  return (
    <Panel className="flex h-full flex-col">
      <PanelHeader>
        <PanelTitle>Response Coordination</PanelTitle>
        {shortfallUnits > 0 ? (
          <Badge tone={ALLOCATION_TONE.CRITICAL}>
            {shortfallUnits} {pluralize(shortfallUnits, "unit")} short
          </Badge>
        ) : (
          <Badge tone={ALLOCATION_TONE.LOW}>Fully resourced</Badge>
        )}
      </PanelHeader>

      <PanelBody className="flex-1 space-y-5 overflow-y-auto">
        <section>
          <SectionHeading icon={<ClipboardList aria-hidden size={11} />}>
            Commander Brief
          </SectionHeading>
          <p className="text-xs leading-relaxed text-slate-300">{brief.incident_summary}</p>
          <dl className="mt-2.5 space-y-1.5">
            <div>
              <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Severity
              </dt>
              <dd className="text-xs text-slate-300">{brief.severity}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Priority
              </dt>
              <dd className="text-xs text-slate-300">{brief.priority}</dd>
            </div>
          </dl>
        </section>

        <section>
          <SectionHeading icon={<Truck aria-hidden size={11} />}>
            Recommended Resources
          </SectionHeading>
          {resources.recommendations.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No resource requirements were derived for this incident.
            </p>
          ) : (
            <ul className="space-y-2">
              {resources.recommendations.map((item, index) => {
                const tone = ALLOCATION_TONE[item.priority];
                return (
                  <motion.li
                    key={item.resource_kind}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(index * 0.04, 0.3), duration: 0.2 }}
                    className="rounded border bg-slate-900/40 p-2.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-medium text-slate-100">
                        <span className="font-mono tabular-nums text-cyan-300">
                          {item.quantity}×
                        </span>{" "}
                        {RESOURCE_LABEL[item.resource_kind]}
                      </span>
                      <Badge tone={tone} className="shrink-0">
                        {item.priority}
                      </Badge>
                    </div>

                    <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
                      {item.reason}
                    </p>

                    <div className="mt-1.5 flex items-center gap-3 text-[11px]">
                      <span className="text-emerald-300">
                        {item.fulfilled_quantity} assigned
                      </span>
                      {item.shortfall > 0 ? (
                        <span className="text-red-300">{item.shortfall} short</span>
                      ) : null}
                    </div>

                    {item.assigned_resource_names.length > 0 ? (
                      <p className="mt-1 truncate font-mono text-[10px] text-slate-500">
                        {item.assigned_resource_names.join(", ")}
                      </p>
                    ) : null}
                  </motion.li>
                );
              })}
            </ul>
          )}
        </section>

        {resources.unmet_requirements.length > 0 ? (
          <section className="rounded-md border border-red-900 bg-red-950/30 p-3">
            <SectionHeading icon={<TriangleAlert aria-hidden size={11} />}>
              Unmet Requirements
            </SectionHeading>
            <ul className="space-y-1">
              {resources.unmet_requirements.map((item) => (
                <li key={item} className="text-xs text-red-100/85">
                  {item}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section>
          <SectionHeading icon={<ListChecks aria-hidden size={11} />}>
            Immediate Actions
          </SectionHeading>
          <ol className="space-y-1.5">
            {brief.immediate_actions.map((action, index) => (
              <motion.li
                key={action}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: Math.min(index * 0.04, 0.3), duration: 0.2 }}
                className="flex gap-2 text-xs text-slate-200"
              >
                <span className="mt-px shrink-0 font-mono text-[10px] tabular-nums text-cyan-400">
                  {String(index + 1).padStart(2, "0")}
                </span>
                {action}
              </motion.li>
            ))}
          </ol>
        </section>

        <section>
          <SectionHeading icon={<Info aria-hidden size={11} />}>Operational Notes</SectionHeading>
          <ul className="space-y-1.5">
            {brief.operational_notes.map((note) => (
              <li key={note} className="flex gap-2 text-[11px] leading-snug text-slate-400">
                <span aria-hidden className="mt-1.5 size-1 shrink-0 rounded-full bg-slate-600" />
                {note}
              </li>
            ))}
          </ul>
        </section>
      </PanelBody>
    </Panel>
  );
}
