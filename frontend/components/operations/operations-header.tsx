"use client";

import { ChevronDown, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Badge, StatusDot } from "@/components/ui/badge";
import { STATUS_TONE, NEUTRAL_TONE } from "@/lib/display";
import { formatClock } from "@/lib/format";
import { useIncidents, useSystemStatus } from "@/lib/queries";
import { useUiStore } from "@/stores/use-ui-store";

const FALLBACK_REGIONS = ["Central Region", "Northern Region", "Southern Region"];

/** Live 24-hour clock, mounted client-side to avoid a server/client time mismatch. */
function OperationsClock() {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="hidden flex-col items-end sm:flex">
      <span className="font-mono text-sm tabular-nums text-slate-100">
        {now ? formatClock(now) : "--:--:--"}
      </span>
      <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
        Local Time
      </span>
    </div>
  );
}

/**
 * Region selector.
 *
 * Options are the locations already present on recorded incidents, so the list reflects where
 * this centre has actually operated rather than an invented geography. The selection is applied
 * as the `location` on subsequent analyses.
 */
function RegionSelector() {
  const { region, setRegion } = useUiStore();
  const { data } = useIncidents(200, 0);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  const recorded = Array.from(
    new Set(
      (data?.incidents ?? [])
        .map((incident) => incident.location)
        .filter((location) => location && location !== "Unknown"),
    ),
  );
  const options = Array.from(new Set([region, ...recorded, ...FALLBACK_REGIONS]));

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="flex items-center gap-2 rounded border px-2.5 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
      >
        <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
          Region
        </span>
        <span className="max-w-[10rem] truncate">{region}</span>
        <ChevronDown aria-hidden size={13} className="text-muted-foreground" />
      </button>

      {open ? (
        <ul
          role="listbox"
          className="absolute right-0 z-40 mt-1 min-w-[13rem] overflow-hidden rounded border bg-card py-1 shadow-xl"
        >
          {options.map((option) => (
            <li key={option}>
              <button
                type="button"
                role="option"
                aria-selected={option === region}
                onClick={() => {
                  setRegion(option);
                  setOpen(false);
                }}
                className={`flex w-full items-center px-3 py-1.5 text-left text-xs transition-colors hover:bg-muted ${
                  option === region ? "text-cyan-300" : "text-slate-300"
                }`}
              >
                {option}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function SystemStatusChip() {
  const { data, isPending, isError } = useSystemStatus();

  if (isPending) {
    return (
      <Badge tone={NEUTRAL_TONE}>
        <StatusDot tone={NEUTRAL_TONE} />
        Checking
      </Badge>
    );
  }
  if (isError || !data) {
    return (
      <Badge tone={STATUS_TONE.OFFLINE}>
        <StatusDot tone={STATUS_TONE.OFFLINE} />
        Backend Offline
      </Badge>
    );
  }

  const tone = STATUS_TONE[data.status];
  const label =
    data.status === "OPERATIONAL"
      ? "All Systems Operational"
      : data.status === "DEGRADED"
        ? "Degraded"
        : "Offline";

  return (
    <Badge tone={tone}>
      <StatusDot tone={tone} className={data.status === "OPERATIONAL" ? "animate-pulse" : ""} />
      {label}
    </Badge>
  );
}

export function OperationsHeader() {
  return (
    <header className="sticky top-0 z-30 border-b bg-slate-950/85 backdrop-blur">
      <div className="flex h-16 items-center justify-between gap-4 px-4 md:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="rounded-md bg-cyan-400/15 p-2 text-cyan-300">
            <ShieldAlert aria-hidden size={20} />
          </div>
          <div className="min-w-0">
            <div className="flex items-baseline gap-2">
              <span className="text-base font-semibold tracking-tight text-slate-50">ARES</span>
              <span className="hidden truncate text-xs text-muted-foreground sm:inline">
                AI Emergency Response Commander
              </span>
            </div>
            <p className="truncate text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">
              Emergency Operations Command Center
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <RegionSelector />
          <SystemStatusChip />
          <OperationsClock />
        </div>
      </div>
    </header>
  );
}
