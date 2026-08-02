/**
 * TypeScript mirror of the ARES backend contract.
 *
 * Field names and unions match the FastAPI schemas exactly. Optional fields are `null` rather
 * than `undefined` because the backend distinguishes "not reported" from "reported as absent",
 * and the UI must preserve that distinction instead of collapsing it to a default.
 */

export type SeverityLevel = "MINOR" | "MODERATE" | "HIGH" | "SEVERE" | "CRITICAL";
export type PriorityLevel = "LOW" | "MODERATE" | "HIGH" | "URGENT" | "CRITICAL";
export type ConfidenceLevel = "VERY_LOW" | "LOW" | "MODERATE" | "HIGH";
export type AllocationPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type ComponentStatus = "OPERATIONAL" | "DEGRADED" | "OFFLINE";

export type DisasterType =
  | "BUILDING_FIRE"
  | "FLOOD"
  | "ROAD_ACCIDENT"
  | "EARTHQUAKE"
  | "BUILDING_COLLAPSE"
  | "CHEMICAL_LEAK"
  | "TRAIN_ACCIDENT"
  | "CYCLONE_STORM"
  | "LANDSLIDE"
  | "UNKNOWN";

export type ResourceKind =
  | "FIRE_TRUCK"
  | "AMBULANCE"
  | "POLICE"
  | "SEARCH_RESCUE"
  | "BOAT"
  | "MEDICAL_TEAM"
  | "HAZMAT"
  | "HEAVY_MACHINERY";

export type IncidentStatus =
  | "CREATED"
  | "ANALYZING"
  | "PLANNED"
  | "RESPONDING"
  | "RESOLVED"
  | "CLOSED";

export interface IncidentAssessment {
  incident_type: string;
  victims: number | null;
  children: number | null;
  elderly: number | null;
  trapped_people: number | null;
  people_detected: number | null;
  passengers_onboard: number | null;
  responders_on_scene: number | null;
  fire_detected: boolean | null;
  smoke_detected: boolean | null;
  collapsed_structure: boolean | null;
  structural_damage: boolean | null;
  hazardous_material: boolean | null;
  toxic_gas_detected: boolean | null;
  explosion_risk: boolean | null;
  gas_station_nearby: boolean | null;
  power_lines_down: boolean | null;
  derailment: boolean | null;
  road_blocked: boolean | null;
  evacuation_required: boolean | null;
  night_time: boolean | null;
  water_level_m: number | null;
  wind_speed_kmh: number | null;
  hospital_distance_km: number | null;
  weather: string | null;
}

export interface ReasoningFactor {
  code: string;
  description: string;
  contribution: number;
}

export interface SeverityDetail {
  score: number;
  level: SeverityLevel;
  factors: ReasoningFactor[];
  applied_floor: string | null;
}

export interface PriorityDetail {
  score: number;
  level: PriorityLevel;
  factors: ReasoningFactor[];
  applied_floor: string | null;
}

export interface ConfidenceDetail {
  confidence: number;
  level: ConfidenceLevel;
  observed_fields: string[];
  missing_fields: string[];
  penalties: ReasoningFactor[];
  applied_cap: string | null;
}

export interface DecisionExplanation {
  current_situation: string;
  severity: string;
  priority: string;
  key_risk_factors: string[];
  recommended_immediate_actions: string[];
  reasoning_summary: string;
}

export interface DecisionResult {
  incident_type: string;
  disaster_type: DisasterType;
  severity_score: number;
  severity_level: SeverityLevel;
  priority_score: number;
  priority_level: PriorityLevel;
  confidence: number;
  confidence_level: ConfidenceLevel;
  recommended_actions: string[];
  risk_factors: string[];
  summary: string;
  explanation: DecisionExplanation;
  severity_detail: SeverityDetail;
  priority_detail: PriorityDetail;
  confidence_detail: ConfidenceDetail;
}

export interface ResourceRecommendation {
  resource_kind: ResourceKind;
  quantity: number;
  priority: AllocationPriority;
  reason: string;
  rule_ids: string[];
  fulfilled_quantity: number;
  shortfall: number;
  assigned_resource_names: string[];
}

export interface AllocationResult {
  recommendations: ResourceRecommendation[];
  total_units_requested: number;
  total_units_fulfilled: number;
  unmet_requirements: string[];
}

export interface CommanderBrief {
  incident_summary: string;
  severity: string;
  priority: string;
  immediate_actions: string[];
  recommended_resources: string[];
  risk_factors: string[];
  operational_notes: string[];
}

export interface DetectionBox {
  detection_class: string;
  confidence: number;
  x1: number | null;
  y1: number | null;
  x2: number | null;
  y2: number | null;
}

export interface Scene {
  detections: DetectionBox[];
  discarded_count: number;
  frame_width: number | null;
  frame_height: number | null;
}

export interface Incident {
  id: string;
  title: string;
  description: string | null;
  incident_type: string;
  status: IncidentStatus;
  priority: string;
  location: string;
  latitude: number | null;
  longitude: number | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentAnalysisResponse {
  incident: Incident;
  assessment: IncidentAssessment;
  decision: DecisionResult;
  resources: AllocationResult;
  commander_brief: CommanderBrief;
  scene: Scene;
  timestamp: string;
}

export interface IncidentSummary {
  id: string;
  title: string;
  incident_type: string;
  status: IncidentStatus;
  priority: string;
  location: string;
  latitude: number | null;
  longitude: number | null;
  severity_level: SeverityLevel | null;
  severity_score: number | null;
  priority_score: number | null;
  confidence: number | null;
  revision_count: number;
  created_at: string;
  updated_at: string;
}

export interface IncidentListResponse {
  incidents: IncidentSummary[];
  total: number;
}

export interface IncidentAnalysisRecord {
  id: string;
  incident_id: string;
  revision: number;
  severity_level: string;
  severity_score: number;
  priority_level: string;
  priority_score: number;
  confidence: number;
  assessment: IncidentAssessment;
  decision: DecisionResult;
  resources: AllocationResult;
  commander_brief: CommanderBrief;
  created_at: string;
}

export interface IncidentTimelineResponse {
  incident: Incident;
  revisions: IncidentAnalysisRecord[];
}

export interface ResourceInventoryItem {
  resource_kind: ResourceKind;
  label: string;
  total: number;
  available: number;
  unavailable: number;
  resource_names: string[];
}

export interface ResourceInventoryResponse {
  items: ResourceInventoryItem[];
  total_units: number;
  available_units: number;
  unrecognised_types: string[];
}

export interface ComponentHealth {
  component: string;
  label: string;
  status: ComponentStatus;
  detail: string;
}

export interface SystemStatusResponse {
  status: ComponentStatus;
  version: string;
  environment: string;
  components: ComponentHealth[];
  checked_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
}

export interface ApiErrorPayload {
  success: false;
  error: { code: string; message: string };
}
