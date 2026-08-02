"use client";

import { AnimatePresence, motion } from "framer-motion";

import { AnalyzeDialog } from "@/components/operations/analyze-dialog";
import { CommandBoard } from "@/components/operations/command-board";
import { OperationsFeed } from "@/components/operations/operations-feed";
import { OperationsHeader } from "@/components/operations/operations-header";
import { OperationsNav } from "@/components/operations/operations-nav";
import { ResourceInventoryView } from "@/components/operations/resource-inventory-view";
import { SystemStatusView } from "@/components/operations/system-status-view";
import { useUiStore } from "@/stores/use-ui-store";

export default function OperationsCenterPage() {
  const activeView = useUiStore((state) => state.activeView);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <OperationsHeader />
      <OperationsNav />

      <main className="flex-1 px-4 py-4 md:px-6 md:py-5">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeView}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            {activeView === "dashboard" ? <CommandBoard /> : null}
            {activeView === "resources" ? <ResourceInventoryView /> : null}
            {activeView === "feed" ? <OperationsFeed /> : null}
            {activeView === "status" ? <SystemStatusView /> : null}
          </motion.div>
        </AnimatePresence>
      </main>

      <AnalyzeDialog />
    </div>
  );
}
