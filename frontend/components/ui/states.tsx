"use client";

import { AlertTriangle, Inbox, Loader2, WifiOff } from "lucide-react";
import type { ReactNode } from "react";

import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

export function LoadingState({ label, className }: { label: string; className?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex items-center justify-center gap-2.5 px-4 py-10 text-sm text-muted-foreground",
        className,
      )}
    >
      <Loader2 aria-hidden className="size-4 animate-spin text-cyan-400" />
      {label}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  className,
}: {
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center px-4 py-12 text-center", className)}>
      <div className="mb-3 text-slate-600">{icon ?? <Inbox aria-hidden size={28} />}</div>
      <p className="text-sm font-medium text-slate-200">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

/**
 * Render a failed request.
 *
 * A connection failure is distinguished from a rejection because the operator's next action
 * differs: one means the backend is unreachable, the other means the request itself was refused.
 */
export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const apiError = error instanceof ApiError ? error : null;
  const offline = apiError?.isConnectionFailure ?? false;
  const message =
    apiError?.message ??
    (error instanceof Error ? error.message : "An unexpected error occurred.");

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center px-4 py-10 text-center",
        className,
      )}
    >
      <div className={cn("mb-3", offline ? "text-amber-400" : "text-red-400")}>
        {offline ? <WifiOff aria-hidden size={26} /> : <AlertTriangle aria-hidden size={26} />}
      </div>
      <p className="text-sm font-medium text-slate-200">
        {offline ? "Backend unreachable" : "Request failed"}
      </p>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 rounded border px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-muted"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
