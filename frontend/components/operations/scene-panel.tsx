"use client";

import { motion } from "framer-motion";
import { ImageOff, ScanSearch } from "lucide-react";
import { useState } from "react";

import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { humanizeCode } from "@/lib/display";
import { formatConfidence } from "@/lib/format";
import type { Scene } from "@/lib/types";

/** Detection classes that indicate a hazard, coloured to stand out from neutral objects. */
const HAZARD_CLASSES = new Set([
  "fire",
  "smoke",
  "flood_water",
  "collapsed_building",
  "debris",
  "power_line",
]);

function boxTone(detectionClass: string): { stroke: string; fill: string; chip: string } {
  if (HAZARD_CLASSES.has(detectionClass)) {
    return {
      stroke: "stroke-red-400",
      fill: "fill-red-500/10",
      chip: "border-red-900 bg-red-950/70 text-red-200",
    };
  }
  if (detectionClass === "person") {
    return {
      stroke: "stroke-amber-300",
      fill: "fill-amber-400/10",
      chip: "border-amber-900 bg-amber-950/70 text-amber-200",
    };
  }
  return {
    stroke: "stroke-cyan-300",
    fill: "fill-cyan-400/10",
    chip: "border-cyan-900 bg-cyan-950/70 text-cyan-200",
  };
}

/**
 * Overlay of backend-supplied detection boxes on the analysed image.
 *
 * Coordinates come from the backend in absolute pixels against the frame it measured, so the
 * overlay is drawn in that coordinate space via a viewBox and scaled by SVG rather than
 * recomputed here. No inference happens in the browser.
 */
function DetectionOverlay({
  imageUrl,
  scene,
  highlighted,
}: {
  imageUrl: string;
  scene: Scene;
  highlighted: number | null;
}) {
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(null);

  const frameWidth = scene.frame_width ?? naturalSize?.width ?? null;
  const frameHeight = scene.frame_height ?? naturalSize?.height ?? null;
  const boxes = scene.detections.filter(
    (detection) =>
      detection.x1 !== null &&
      detection.y1 !== null &&
      detection.x2 !== null &&
      detection.y2 !== null,
  );
  const canOverlay = frameWidth !== null && frameHeight !== null && boxes.length > 0;

  return (
    <div className="relative overflow-hidden rounded-md border bg-slate-950">
      {/* eslint-disable-next-line @next/next/no-img-element -- object URL of a client-side upload */}
      <img
        src={imageUrl}
        alt="Analysed incident scene"
        className="block max-h-[22rem] w-full object-contain"
        onLoad={(event) =>
          setNaturalSize({
            width: event.currentTarget.naturalWidth,
            height: event.currentTarget.naturalHeight,
          })
        }
      />

      {canOverlay ? (
        <svg
          viewBox={`0 0 ${frameWidth} ${frameHeight}`}
          preserveAspectRatio="xMidYMid meet"
          className="pointer-events-none absolute inset-0 size-full"
          aria-hidden
        >
          {boxes.map((detection, index) => {
            const tone = boxTone(detection.detection_class);
            const dimmed = highlighted !== null && highlighted !== index;
            return (
              <g key={`${detection.detection_class}-${index}`} opacity={dimmed ? 0.25 : 1}>
                <rect
                  x={detection.x1 as number}
                  y={detection.y1 as number}
                  width={(detection.x2 as number) - (detection.x1 as number)}
                  height={(detection.y2 as number) - (detection.y1 as number)}
                  className={`${tone.stroke} ${tone.fill}`}
                  strokeWidth={Math.max(2, frameWidth / 320)}
                  vectorEffect="non-scaling-stroke"
                />
              </g>
            );
          })}
        </svg>
      ) : null}

      {scene.frame_width === null && boxes.length > 0 ? (
        <p className="border-t bg-slate-900/80 px-3 py-1.5 text-[11px] text-muted-foreground">
          Frame geometry not reported by the detector; overlay scaled to the displayed image.
        </p>
      ) : null}
    </div>
  );
}

export function ScenePanel({
  imageUrl,
  scene,
}: {
  imageUrl: string | null;
  scene: Scene;
}) {
  const [highlighted, setHighlighted] = useState<number | null>(null);

  const withBoxes = scene.detections.filter((detection) => detection.x1 !== null);

  return (
    <Panel className="flex h-full flex-col">
      <PanelHeader>
        <PanelTitle>Scene</PanelTitle>
        <span className="text-[11px] text-muted-foreground">
          {scene.detections.length} detected
          {scene.discarded_count > 0 ? ` · ${scene.discarded_count} discarded` : ""}
        </span>
      </PanelHeader>

      <PanelBody className="flex-1 space-y-4 overflow-y-auto">
        {imageUrl ? (
          <DetectionOverlay imageUrl={imageUrl} scene={scene} highlighted={highlighted} />
        ) : (
          <div className="flex flex-col items-center gap-2 rounded-md border border-dashed bg-slate-900/30 px-4 py-10 text-center">
            <ImageOff aria-hidden size={22} className="text-slate-600" />
            <p className="text-xs text-muted-foreground">
              Source imagery is held for the active session only and is not retained by the
              backend. Detections below remain on record.
            </p>
          </div>
        )}

        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            Detected Objects
          </p>

          {scene.detections.length === 0 ? (
            <EmptyState
              icon={<ScanSearch aria-hidden size={24} />}
              title="No objects detected"
              description="The detector returned no recognised objects for this image."
              className="py-6"
            />
          ) : (
            <ul className="space-y-1.5">
              {scene.detections.map((detection, index) => {
                const tone = boxTone(detection.detection_class);
                const hasBox = detection.x1 !== null;
                return (
                  <motion.li
                    key={`${detection.detection_class}-${index}`}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(index * 0.03, 0.3), duration: 0.2 }}
                    onMouseEnter={() => hasBox && setHighlighted(withBoxes.indexOf(detection))}
                    onMouseLeave={() => setHighlighted(null)}
                    className="flex items-center justify-between gap-3 rounded border bg-slate-900/40 px-2.5 py-1.5"
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <span
                        className={`inline-block size-2 shrink-0 rounded-sm border ${tone.chip}`}
                      />
                      <span className="truncate text-xs text-slate-200">
                        {humanizeCode(detection.detection_class)}
                      </span>
                    </span>
                    <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                      {formatConfidence(detection.confidence)}
                    </span>
                  </motion.li>
                );
              })}
            </ul>
          )}
        </div>
      </PanelBody>
    </Panel>
  );
}
