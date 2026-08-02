"use client";

import { Clock, FileImage, Video } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { PIPELINE_STAGES, PipelineProgress } from "@/components/operations/pipeline-progress";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ErrorState } from "@/components/ui/states";
import { useAnalyzeIncident } from "@/lib/queries";
import { useUiStore } from "@/stores/use-ui-store";

/** Extensions the backend's image intake accepts. */
const ACCEPTED_IMAGE_TYPES = "image/jpeg,image/png,image/bmp,image/webp,image/tiff";

/**
 * Expected duration of each stage, used only to advance the display while the single
 * synchronous request is in flight. The last stage never auto-completes.
 */
const STAGE_DURATION_MS = 550;

export function AnalyzeDialog() {
  const { isAnalyzeOpen, setAnalyzeOpen, setActiveAnalysis, region, setActiveView } =
    useUiStore();
  const analyze = useAnalyzeIncident();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [stageIndex, setStageIndex] = useState(0);

  const isRunning = analyze.isPending;

  // Advance the stage display while the request is in flight, stopping before the final stage
  // so completion is only ever shown once the backend has actually responded.
  useEffect(() => {
    if (!isRunning) return;
    setStageIndex(0);
    const timer = window.setInterval(() => {
      setStageIndex((current) => Math.min(current + 1, PIPELINE_STAGES.length - 1));
    }, STAGE_DURATION_MS);
    return () => window.clearInterval(timer);
  }, [isRunning]);

  function reset() {
    analyze.reset();
    setStageIndex(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleOpenChange(open: boolean) {
    if (isRunning) return;
    setAnalyzeOpen(open);
    if (!open) reset();
  }

  function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    const objectUrl = URL.createObjectURL(file);
    analyze.mutate(
      { image: file, location: region },
      {
        onSuccess: (response) => {
          setStageIndex(PIPELINE_STAGES.length);
          setActiveAnalysis(response, objectUrl);
          setActiveView("dashboard");
          window.setTimeout(() => {
            setAnalyzeOpen(false);
            reset();
          }, 450);
        },
        onError: () => {
          URL.revokeObjectURL(objectUrl);
        },
      },
    );
  }

  return (
    <Dialog open={isAnalyzeOpen} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isRunning ? "Analysing Incident" : "Analyze New Incident"}</DialogTitle>
          <DialogDescription>
            {isRunning
              ? "Running the deterministic decision pipeline. Do not close this window."
              : `Submit scene imagery for analysis. Recorded against ${region}.`}
          </DialogDescription>
        </DialogHeader>

        {isRunning ? (
          <PipelineProgress activeIndex={stageIndex} />
        ) : analyze.isError ? (
          <div>
            <ErrorState error={analyze.error} onRetry={reset} className="py-6" />
          </div>
        ) : (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex w-full items-start gap-3 rounded-md border bg-slate-900/40 p-4 text-left transition-colors hover:border-cyan-400/40 hover:bg-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
            >
              <span className="rounded bg-cyan-400/15 p-2 text-cyan-300">
                <FileImage aria-hidden size={18} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium text-slate-100">Image Analysis</span>
                <span className="block text-xs text-muted-foreground">
                  JPEG, PNG, BMP, WEBP, or TIFF. Analysis begins on selection.
                </span>
              </span>
            </button>

            <div
              aria-disabled
              className="flex w-full cursor-not-allowed items-start gap-3 rounded-md border border-dashed bg-slate-900/20 p-4 text-left opacity-60"
            >
              <span className="rounded bg-slate-800 p-2 text-slate-500">
                <Video aria-hidden size={18} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-400">Video Analysis</span>
                  <span className="inline-flex items-center gap-1 rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    <Clock aria-hidden size={9} />
                    Coming Soon
                  </span>
                </span>
                <span className="block text-xs text-muted-foreground">
                  Frame-sequence analysis is not yet available.
                </span>
              </span>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_IMAGE_TYPES}
              onChange={handleFileSelected}
              className="hidden"
              aria-label="Select incident image"
            />

            <div className="flex justify-end pt-1">
              <Button variant="outline" size="sm" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
