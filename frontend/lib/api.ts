/**
 * Axios client and typed calls for every ARES backend endpoint.
 *
 * The backend mounts its routes at the root; the configured API prefix only serves the OpenAPI
 * documents, so requests must not be prefixed with it.
 */

import axios, { AxiosError } from "axios";

import type {
  ApiErrorPayload,
  HealthResponse,
  IncidentAnalysisResponse,
  IncidentListResponse,
  IncidentTimelineResponse,
  ResourceInventoryResponse,
  SystemStatusResponse,
} from "@/lib/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000,
  headers: { Accept: "application/json" },
});

/** An API failure carrying the backend's own error code where one was returned. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number | null;

  constructor(message: string, code: string, status: number | null) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }

  /** Whether the request never reached the server. */
  get isConnectionFailure(): boolean {
    return this.status === null;
  }
}

function toApiError(error: unknown): ApiError {
  if (!axios.isAxiosError(error)) {
    return new ApiError(
      error instanceof Error ? error.message : "Unexpected client error.",
      "client_error",
      null,
    );
  }

  const axiosError = error as AxiosError<ApiErrorPayload>;
  const status = axiosError.response?.status ?? null;

  if (status === null) {
    return new ApiError(
      "Cannot reach the ARES backend. Confirm the service is running.",
      "connection_failed",
      null,
    );
  }

  const payload = axiosError.response?.data;
  if (payload && typeof payload === "object" && "error" in payload && payload.error) {
    return new ApiError(payload.error.message, payload.error.code, status);
  }

  if (status === 422) {
    return new ApiError("The request was rejected as invalid.", "validation_error", status);
  }

  return new ApiError(axiosError.message || "The request failed.", "request_failed", status);
}

async function request<T>(operation: () => Promise<{ data: T }>): Promise<T> {
  try {
    const response = await operation();
    return response.data;
  } catch (error) {
    throw toApiError(error);
  }
}

export interface AnalyzeIncidentInput {
  image: File;
  location?: string;
  title?: string;
  latitude?: number;
  longitude?: number;
}

function buildAnalyzeForm(input: AnalyzeIncidentInput): FormData {
  const form = new FormData();
  form.append("image", input.image);
  if (input.location?.trim()) form.append("location", input.location.trim());
  if (input.title?.trim()) form.append("title", input.title.trim());
  if (typeof input.latitude === "number") form.append("latitude", String(input.latitude));
  if (typeof input.longitude === "number") form.append("longitude", String(input.longitude));
  return form;
}

export function getHealth(): Promise<HealthResponse> {
  return request(() => apiClient.get<HealthResponse>("/health"));
}

export function getSystemStatus(): Promise<SystemStatusResponse> {
  return request(() => apiClient.get<SystemStatusResponse>("/system/status"));
}

export function getResourceInventory(): Promise<ResourceInventoryResponse> {
  return request(() => apiClient.get<ResourceInventoryResponse>("/resources/inventory"));
}

export function listIncidents(limit = 50, offset = 0): Promise<IncidentListResponse> {
  return request(() =>
    apiClient.get<IncidentListResponse>("/incidents", { params: { limit, offset } }),
  );
}

export function getIncidentTimeline(incidentId: string): Promise<IncidentTimelineResponse> {
  return request(() =>
    apiClient.get<IncidentTimelineResponse>(`/incidents/${incidentId}/timeline`),
  );
}

export function analyzeIncident(input: AnalyzeIncidentInput): Promise<IncidentAnalysisResponse> {
  return request(() =>
    apiClient.post<IncidentAnalysisResponse>("/incidents/analyze", buildAnalyzeForm(input)),
  );
}

export function reanalyzeIncident(
  incidentId: string,
  image: File,
): Promise<IncidentAnalysisResponse> {
  const form = new FormData();
  form.append("image", image);
  return request(() =>
    apiClient.post<IncidentAnalysisResponse>(`/incidents/${incidentId}/analyze`, form),
  );
}
