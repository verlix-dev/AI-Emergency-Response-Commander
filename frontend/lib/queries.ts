/**
 * TanStack Query hooks over the ARES API.
 *
 * Polling intervals are deliberately conservative: status and inventory change slowly, and an
 * operations centre display should not generate constant network traffic.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  analyzeIncident,
  getIncidentTimeline,
  getResourceInventory,
  getSystemStatus,
  listIncidents,
  reanalyzeIncident,
  type AnalyzeIncidentInput,
} from "@/lib/api";
import type { IncidentAnalysisResponse } from "@/lib/types";

export const queryKeys = {
  systemStatus: ["system-status"] as const,
  inventory: ["resource-inventory"] as const,
  incidents: (limit: number, offset: number) => ["incidents", limit, offset] as const,
  timeline: (incidentId: string) => ["incident-timeline", incidentId] as const,
};

const STATUS_POLL_MS = 30_000;
const INVENTORY_POLL_MS = 60_000;
const FEED_POLL_MS = 45_000;

/** Do not retry a request the server explicitly rejected; only retry transport failures. */
function retryTransportOnly(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && !error.isConnectionFailure) return false;
  return failureCount < 2;
}

export function useSystemStatus() {
  return useQuery({
    queryKey: queryKeys.systemStatus,
    queryFn: getSystemStatus,
    refetchInterval: STATUS_POLL_MS,
    retry: retryTransportOnly,
  });
}

export function useResourceInventory() {
  return useQuery({
    queryKey: queryKeys.inventory,
    queryFn: getResourceInventory,
    refetchInterval: INVENTORY_POLL_MS,
    retry: retryTransportOnly,
  });
}

export function useIncidents(limit = 50, offset = 0) {
  return useQuery({
    queryKey: queryKeys.incidents(limit, offset),
    queryFn: () => listIncidents(limit, offset),
    refetchInterval: FEED_POLL_MS,
    retry: retryTransportOnly,
  });
}

export function useIncidentTimeline(incidentId: string | null) {
  return useQuery({
    queryKey: queryKeys.timeline(incidentId ?? "none"),
    queryFn: () => getIncidentTimeline(incidentId as string),
    enabled: incidentId !== null,
    retry: retryTransportOnly,
  });
}

/** Invalidate every list affected by a completed analysis. */
function useAnalysisInvalidation() {
  const queryClient = useQueryClient();
  return (response: IncidentAnalysisResponse) => {
    void queryClient.invalidateQueries({ queryKey: ["incidents"] });
    void queryClient.invalidateQueries({ queryKey: queryKeys.inventory });
    void queryClient.invalidateQueries({
      queryKey: queryKeys.timeline(response.incident.id),
    });
  };
}

export function useAnalyzeIncident() {
  const invalidate = useAnalysisInvalidation();
  return useMutation<IncidentAnalysisResponse, ApiError, AnalyzeIncidentInput>({
    mutationFn: analyzeIncident,
    onSuccess: invalidate,
  });
}

export function useReanalyzeIncident() {
  const invalidate = useAnalysisInvalidation();
  return useMutation<IncidentAnalysisResponse, ApiError, { incidentId: string; image: File }>({
    mutationFn: ({ incidentId, image }) => reanalyzeIncident(incidentId, image),
    onSuccess: invalidate,
  });
}
