/**
 * Formatting helpers for operational readouts.
 *
 * Times render in 24-hour form throughout, which is the convention in emergency operations and
 * removes AM/PM ambiguity from timestamped records.
 */

const DATE_TIME = new Intl.DateTimeFormat("en-GB", {
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const TIME_ONLY = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

/** Format an ISO timestamp as a date and 24-hour time. */
export function formatDateTime(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return "Unknown";
  return DATE_TIME.format(date);
}

/** Format a clock time including seconds. */
export function formatClock(value: Date): string {
  return TIME_ONLY.format(value);
}

/** Describe how long ago a timestamp occurred, in operational shorthand. */
export function formatRelative(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return "Unknown";

  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 10) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? "1 day ago" : `${days} days ago`;
}

/** Render a 0-1 confidence as a whole percentage. */
export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

/** Render a score to at most one decimal place, dropping a trailing zero. */
export function formatScore(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

/** Render an optional measurement with its unit, or a dash when unreported. */
export function formatMeasurement(value: number | null, unit: string): string {
  return value === null ? "—" : `${formatScore(value)} ${unit}`;
}

/**
 * Render a tri-state boolean the way the backend means it.
 *
 * `null` is "not reported" rather than "absent", and must never display as "No".
 */
export function formatFlag(value: boolean | null): string {
  if (value === null) return "Not reported";
  return value ? "Confirmed" : "Reported absent";
}

/** Render an optional count, distinguishing zero from unreported. */
export function formatCount(value: number | null): string {
  return value === null ? "—" : String(value);
}

/** Pluralise a noun against a count. */
export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : (plural ?? `${singular}s`);
}
