"use client";

import { Activity, LayoutDashboard, Radio, Server } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { type OperationsView, useUiStore } from "@/stores/use-ui-store";

const NAV_ITEMS: { view: OperationsView; label: string; icon: React.ReactNode }[] = [
  { view: "dashboard", label: "Command Board", icon: <LayoutDashboard aria-hidden size={14} /> },
  { view: "resources", label: "Resources", icon: <Activity aria-hidden size={14} /> },
  { view: "feed", label: "Operations Feed", icon: <Radio aria-hidden size={14} /> },
  { view: "status", label: "System Status", icon: <Server aria-hidden size={14} /> },
];

export function OperationsNav() {
  const { activeView, setActiveView, setAnalyzeOpen } = useUiStore();

  return (
    <div className="flex items-center justify-between gap-4 border-b bg-slate-950/50 px-4 md:px-6">
      <nav aria-label="Operations sections" className="-mb-px flex gap-1 overflow-x-auto">
        {NAV_ITEMS.map((item) => {
          const active = activeView === item.view;
          return (
            <button
              key={item.view}
              type="button"
              onClick={() => setActiveView(item.view)}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-3 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cyan-400",
                active
                  ? "border-cyan-400 text-cyan-300"
                  : "border-transparent text-muted-foreground hover:text-slate-200",
              )}
            >
              {item.icon}
              {item.label}
            </button>
          );
        })}
      </nav>

      <Button size="sm" onClick={() => setAnalyzeOpen(true)} className="shrink-0">
        Analyze New Incident
      </Button>
    </div>
  );
}
