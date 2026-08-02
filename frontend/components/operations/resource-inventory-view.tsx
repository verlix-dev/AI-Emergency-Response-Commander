"use client";

import { motion } from "framer-motion";
import { PackageSearch, TriangleAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { ALLOCATION_TONE, RESOURCE_LABEL, STATUS_TONE } from "@/lib/display";
import { pluralize } from "@/lib/format";
import { useResourceInventory } from "@/lib/queries";
import type { AllocationResult, ResourceKind } from "@/lib/types";
import { useUiStore } from "@/stores/use-ui-store";

interface InventoryRow {
  kind: ResourceKind;
  label: string;
  available: number;
  total: number;
  required: number;
  remaining: number;
  shortfall: number;
}

/**
 * Merge standing stock with the live requirement from the active analysis.
 *
 * "Required" and "remaining" only have meaning while an analysis is on the board; without one
 * the inventory reports stock alone rather than inventing a demand figure.
 */
function buildRows(
  items: { resource_kind: ResourceKind; label: string; total: number; available: number }[],
  allocation: AllocationResult | null,
): InventoryRow[] {
  const required = new Map<ResourceKind, { quantity: number; shortfall: number }>();
  for (const recommendation of allocation?.recommendations ?? []) {
    required.set(recommendation.resource_kind, {
      quantity: recommendation.quantity,
      shortfall: recommendation.shortfall,
    });
  }

  const kinds = new Set<ResourceKind>([
    ...items.map((item) => item.resource_kind),
    ...required.keys(),
  ]);

  return Array.from(kinds)
    .map((kind) => {
      const stock = items.find((item) => item.resource_kind === kind);
      const demand = required.get(kind);
      const available = stock?.available ?? 0;
      const quantity = demand?.quantity ?? 0;
      return {
        kind,
        label: stock?.label ?? RESOURCE_LABEL[kind],
        available,
        total: stock?.total ?? 0,
        required: quantity,
        remaining: Math.max(0, available - quantity),
        shortfall: demand?.shortfall ?? Math.max(0, quantity - available),
      };
    })
    .sort((first, second) => second.shortfall - first.shortfall || first.label.localeCompare(second.label));
}

function InventoryBar({ row }: { row: InventoryRow }) {
  const capacity = Math.max(row.total, row.required, 1);
  const committedPercent = Math.min(100, (Math.min(row.required, row.available) / capacity) * 100);
  const remainingPercent = Math.min(100, (row.remaining / capacity) * 100);

  return (
    <div className="flex h-1.5 overflow-hidden rounded-full bg-slate-800">
      <motion.div
        className="h-full bg-cyan-500"
        initial={{ width: 0 }}
        animate={{ width: `${committedPercent}%` }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      />
      <motion.div
        className="h-full bg-emerald-600/70"
        initial={{ width: 0 }}
        animate={{ width: `${remainingPercent}%` }}
        transition={{ duration: 0.5, ease: "easeOut", delay: 0.1 }}
      />
    </div>
  );
}

export function ResourceInventoryView() {
  const { data, isPending, isError, error, refetch } = useResourceInventory();
  const activeAnalysis = useUiStore((state) => state.activeAnalysis);
  const region = useUiStore((state) => state.region);

  if (isPending) return <LoadingState label="Loading resource inventory…" />;
  if (isError) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const rows = buildRows(data.items, activeAnalysis?.resources ?? null);
  const shortfalls = rows.filter((row) => row.shortfall > 0);

  return (
    <div className="space-y-4">
      <Panel>
        <PanelHeader>
          <div>
            <PanelTitle>Resource Inventory</PanelTitle>
            <p className="mt-0.5 text-[11px] text-muted-foreground">{region}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone={STATUS_TONE.OPERATIONAL}>
              {data.available_units} available
            </Badge>
            <Badge>{data.total_units} total</Badge>
          </div>
        </PanelHeader>

        <PanelBody>
          {rows.length === 0 ? (
            <EmptyState
              icon={<PackageSearch aria-hidden size={26} />}
              title="No resources registered"
              description="The backend resource pool is empty. Allocations will report every requirement as a shortfall until units are registered."
            />
          ) : (
            <>
              <div className="mb-3 grid grid-cols-[1fr_auto_auto_auto] gap-x-4 gap-y-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                <span>Resource</span>
                <span className="w-14 text-right">Available</span>
                <span className="w-14 text-right">Required</span>
                <span className="w-14 text-right">Remaining</span>
              </div>

              <ul className="space-y-3">
                {rows.map((row, index) => (
                  <motion.li
                    key={row.kind}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(index * 0.04, 0.3), duration: 0.2 }}
                  >
                    <div className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-x-4">
                      <span className="flex items-center gap-2 truncate text-xs text-slate-100">
                        {row.label}
                        {row.shortfall > 0 ? (
                          <Badge tone={ALLOCATION_TONE.CRITICAL} className="shrink-0">
                            −{row.shortfall}
                          </Badge>
                        ) : null}
                      </span>
                      <span className="w-14 text-right font-mono text-xs tabular-nums text-slate-200">
                        {row.available}
                        <span className="text-slate-600">/{row.total}</span>
                      </span>
                      <span className="w-14 text-right font-mono text-xs tabular-nums text-cyan-300">
                        {row.required || "—"}
                      </span>
                      <span
                        className={`w-14 text-right font-mono text-xs tabular-nums ${
                          row.shortfall > 0 ? "text-red-300" : "text-emerald-300"
                        }`}
                      >
                        {row.required ? row.remaining : "—"}
                      </span>
                    </div>
                    <div className="mt-1.5">
                      <InventoryBar row={row} />
                    </div>
                  </motion.li>
                ))}
              </ul>
            </>
          )}

          {data.unrecognised_types.length > 0 ? (
            <p className="mt-4 border-t pt-3 text-[11px] text-muted-foreground">
              Not allocatable: {data.unrecognised_types.join(", ")} — these resource types are
              outside the allocation vocabulary and are excluded from matching.
            </p>
          ) : null}
        </PanelBody>
      </Panel>

      {shortfalls.length > 0 ? (
        <Panel className="border-red-900/60">
          <PanelHeader className="border-red-900/60">
            <PanelTitle className="text-red-300">Mutual Aid Recommended</PanelTitle>
            <TriangleAlert aria-hidden size={14} className="text-red-400" />
          </PanelHeader>
          <PanelBody>
            <p className="text-xs text-slate-300">
              The active incident requires{" "}
              {shortfalls.reduce((total, row) => total + row.shortfall, 0)} more{" "}
              {pluralize(
                shortfalls.reduce((total, row) => total + row.shortfall, 0),
                "unit",
              )}{" "}
              than {region} currently has available. Request support from a neighbouring region
              before committing to the full plan.
            </p>
            <ul className="mt-3 space-y-1.5">
              {shortfalls.map((row) => (
                <li key={row.kind} className="flex justify-between gap-3 text-xs">
                  <span className="text-slate-200">{row.label}</span>
                  <span className="font-mono tabular-nums text-red-300">
                    {row.shortfall} short of {row.required}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-3 border-t pt-2.5 text-[11px] text-muted-foreground">
              Supporting region and estimated response time are not modelled by the backend, so
              they are not shown. Escalate through existing mutual-aid procedure.
            </p>
          </PanelBody>
        </Panel>
      ) : null}
    </div>
  );
}
