/**
 * Presentation mappings for operational values.
 *
 * Status colour is reserved for meaning: green through red communicates severity, urgency, and
 * readiness only. No other palette carries semantic weight, so a commander can read state from
 * colour alone without learning a legend.
 */

import type {
  AllocationPriority,
  ComponentStatus,
  ConfidenceLevel,
  DisasterType,
  PriorityLevel,
  ResourceKind,
  SeverityLevel,
} from "@/lib/types";

export interface ToneClasses {
  text: string;
  border: string;
  background: string;
  dot: string;
  bar: string;
}

const TONES = {
  neutral: {
    text: "text-slate-300",
    border: "border-slate-700",
    background: "bg-slate-800/40",
    dot: "bg-slate-400",
    bar: "bg-slate-500",
  },
  info: {
    text: "text-sky-300",
    border: "border-sky-900",
    background: "bg-sky-950/40",
    dot: "bg-sky-400",
    bar: "bg-sky-500",
  },
  ok: {
    text: "text-emerald-300",
    border: "border-emerald-900",
    background: "bg-emerald-950/40",
    dot: "bg-emerald-400",
    bar: "bg-emerald-500",
  },
  caution: {
    text: "text-amber-300",
    border: "border-amber-900",
    background: "bg-amber-950/40",
    dot: "bg-amber-400",
    bar: "bg-amber-500",
  },
  elevated: {
    text: "text-orange-300",
    border: "border-orange-900",
    background: "bg-orange-950/40",
    dot: "bg-orange-400",
    bar: "bg-orange-500",
  },
  critical: {
    text: "text-red-300",
    border: "border-red-900",
    background: "bg-red-950/40",
    dot: "bg-red-400",
    bar: "bg-red-500",
  },
} as const satisfies Record<string, ToneClasses>;

export const SEVERITY_TONE: Record<SeverityLevel, ToneClasses> = {
  MINOR: TONES.ok,
  MODERATE: TONES.caution,
  HIGH: TONES.elevated,
  SEVERE: TONES.critical,
  CRITICAL: TONES.critical,
};

export const PRIORITY_TONE: Record<PriorityLevel, ToneClasses> = {
  LOW: TONES.ok,
  MODERATE: TONES.caution,
  HIGH: TONES.elevated,
  URGENT: TONES.critical,
  CRITICAL: TONES.critical,
};

export const CONFIDENCE_TONE: Record<ConfidenceLevel, ToneClasses> = {
  VERY_LOW: TONES.critical,
  LOW: TONES.elevated,
  MODERATE: TONES.caution,
  HIGH: TONES.ok,
};

export const ALLOCATION_TONE: Record<AllocationPriority, ToneClasses> = {
  CRITICAL: TONES.critical,
  HIGH: TONES.elevated,
  MEDIUM: TONES.caution,
  LOW: TONES.info,
};

export const STATUS_TONE: Record<ComponentStatus, ToneClasses> = {
  OPERATIONAL: TONES.ok,
  DEGRADED: TONES.caution,
  OFFLINE: TONES.critical,
};

export const NEUTRAL_TONE: ToneClasses = TONES.neutral;

export const DISASTER_LABEL: Record<DisasterType, string> = {
  BUILDING_FIRE: "Building Fire",
  FLOOD: "Flood",
  ROAD_ACCIDENT: "Road Accident",
  EARTHQUAKE: "Earthquake",
  BUILDING_COLLAPSE: "Building Collapse",
  CHEMICAL_LEAK: "Chemical / Gas Leak",
  TRAIN_ACCIDENT: "Train Accident",
  CYCLONE_STORM: "Cyclone / Storm",
  LANDSLIDE: "Landslide",
  UNKNOWN: "Unclassified",
};

export const RESOURCE_LABEL: Record<ResourceKind, string> = {
  FIRE_TRUCK: "Fire Trucks",
  AMBULANCE: "Ambulances",
  POLICE: "Police Units",
  SEARCH_RESCUE: "Search & Rescue",
  BOAT: "Boats",
  MEDICAL_TEAM: "Medical Teams",
  HAZMAT: "Hazmat Units",
  HEAVY_MACHINERY: "Heavy Equipment",
};

/** Human-readable label for a disaster type, tolerating values outside the known union. */
export function disasterLabel(value: string): string {
  return (
    DISASTER_LABEL[value as DisasterType] ??
    value
      .split("_")
      .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
      .join(" ")
  );
}

/** Convert an UPPER_SNAKE code into readable words, for rule identifiers and field names. */
export function humanizeCode(value: string): string {
  return value
    .replace(/[._]/g, " ")
    .toLowerCase()
    .replace(/^\w/, (character) => character.toUpperCase());
}
