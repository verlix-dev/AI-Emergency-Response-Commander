"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { AlertTriangle, MapPin, ShieldQuestion } from "lucide-react";
import { useEffect } from "react";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelBody, PanelHeader, PanelTitle } from "@/components/ui/card";
import {
  CONFIDENCE_TONE,
  PRIORITY_TONE,
  SEVERITY_TONE,
  disasterLabel,
  humanizeCode,
} from "@/lib/display";
import { formatConfidence, formatScore } from "@/lib/format";
import type { DecisionResult, Incident } from "@/lib/types";

/** A score that counts up on mount, drawing the eye to a changed grading. */
function CountUpScore({ value, className }: { value: number; className?: string }) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 90, damping: 20 });
  const rounded = useTransform(spring, (current) => formatScore(Math.round(current * 10) / 10));

  useEffect(() => {
    motionValue.set(value);
  }, [motionValue, value]);

  return <motion.span className={className}>{rounded}</motion.span>;
}

function GradeTile({
  label,
  level,
  score,
  tone,
  suffix,
}: {
  label: string;
  level: string;
  score: number;
  tone: { text: string; border: string; background: string; bar: string };
  suffix: string;
}) {
  return (
    <div className={`rounded-md border p-3 ${tone.border} ${tone.background}`}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </p>
      <p className={`mt-1.5 text-lg font-semibold leading-none ${tone.text}`}>{level}</p>
      <div className="mt-2 flex items-baseline gap-1">
        <CountUpScore
          value={score}
          className="font-mono text-xs tabular-nums text-slate-300"
        />
        <span className="text-[10px] text-muted-foreground">{suffix}</span>
      </div>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-800">
        <motion.div
          className={`h-full ${tone.bar}`}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, score)}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

export function DecisionPanel({
  decision,
  incident,
}: {
  decision: DecisionResult;
  incident: Incident;
}) {
  const severityTone = SEVERITY_TONE[decision.severity_level];
  const priorityTone = PRIORITY_TONE[decision.priority_level];
  const confidenceTone = CONFIDENCE_TONE[decision.confidence_level];

  return (
    <Panel className="flex h-full flex-col">
      <PanelHeader>
        <PanelTitle>Decision Intelligence</PanelTitle>
        <Badge tone={severityTone}>{decision.severity_level}</Badge>
      </PanelHeader>

      <PanelBody className="flex-1 space-y-5 overflow-y-auto">
        <div>
          <h3 className="text-xl font-semibold tracking-tight text-slate-50">
            {disasterLabel(decision.disaster_type)}
          </h3>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            <MapPin aria-hidden size={12} />
            {incident.location}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-3">
          <GradeTile
            label="Severity"
            level={decision.severity_level}
            score={decision.severity_score}
            tone={severityTone}
            suffix="/ 100"
          />
          <GradeTile
            label="Priority"
            level={decision.priority_level}
            score={decision.priority_score}
            tone={priorityTone}
            suffix="/ 100"
          />
          <div
            className={`col-span-2 rounded-md border p-3 lg:col-span-1 ${confidenceTone.border} ${confidenceTone.background}`}
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Confidence
            </p>
            <p className={`mt-1.5 text-lg font-semibold leading-none ${confidenceTone.text}`}>
              {decision.confidence_level.replace("_", " ")}
            </p>
            <p className="mt-2 font-mono text-xs tabular-nums text-slate-300">
              {formatConfidence(decision.confidence)}
            </p>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-800">
              <motion.div
                className={`h-full ${confidenceTone.bar}`}
                initial={{ width: 0 }}
                animate={{ width: `${decision.confidence * 100}%` }}
                transition={{ duration: 0.6, ease: "easeOut" }}
              />
            </div>
          </div>
        </div>

        {decision.severity_detail.applied_floor || decision.priority_detail.applied_floor ? (
          <div className="space-y-1.5 rounded-md border border-amber-900 bg-amber-950/30 p-3">
            <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-300">
              <AlertTriangle aria-hidden size={11} />
              Minimum Grading Applied
            </p>
            {decision.severity_detail.applied_floor ? (
              <p className="text-xs text-amber-100/80">
                Severity raised by rule {humanizeCode(decision.severity_detail.applied_floor)}.
              </p>
            ) : null}
            {decision.priority_detail.applied_floor ? (
              <p className="text-xs text-amber-100/80">
                Urgency raised by rule {humanizeCode(decision.priority_detail.applied_floor)}.
              </p>
            ) : null}
          </div>
        ) : null}

        <section>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            Risk Factors
          </p>
          {decision.risk_factors.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No contributing risk factors were identified.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {decision.risk_factors.map((factor, index) => (
                <motion.li
                  key={factor}
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: Math.min(index * 0.04, 0.3), duration: 0.2 }}
                  className="flex gap-2 text-xs text-slate-200"
                >
                  <span aria-hidden className="mt-1.5 size-1 shrink-0 rounded-full bg-red-400" />
                  {factor}
                </motion.li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            Explanation
          </p>
          <p className="text-xs leading-relaxed text-slate-300">
            {decision.explanation.current_situation}
          </p>
          <p className="mt-2.5 text-xs leading-relaxed text-slate-400">
            {decision.explanation.reasoning_summary}
          </p>
        </section>

        {decision.confidence_detail.missing_fields.length > 0 ? (
          <section className="rounded-md border bg-slate-900/40 p-3">
            <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              <ShieldQuestion aria-hidden size={11} />
              Unreported Information
            </p>
            <p className="text-xs text-slate-400">
              {decision.confidence_detail.missing_fields.map(humanizeCode).join(", ")}.
            </p>
            <p className="mt-1.5 text-[11px] text-muted-foreground">
              Severity and priority were not reduced because of these gaps.
            </p>
          </section>
        ) : null}
      </PanelBody>
    </Panel>
  );
}
