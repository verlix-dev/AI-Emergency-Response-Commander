"""Pydantic schemas for the end-to-end incident analysis workflow."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.engines.allocation_models import AllocationResult
from app.engines.models import DecisionResult, IncidentAssessment
from app.schemas.base import ORMResponseSchema
from app.schemas.incident import IncidentResponseSchema


class CommanderBrief(BaseModel):
    """A deterministic operational briefing assembled from a completed analysis."""

    incident_summary: str
    severity: str
    priority: str
    immediate_actions: list[str]
    recommended_resources: list[str]
    risk_factors: list[str]
    operational_notes: list[str]

    def as_text(self) -> str:
        """Render the brief as plain text for storage and display."""
        sections: list[str] = [
            "INCIDENT SUMMARY",
            self.incident_summary,
            "",
            "SEVERITY",
            self.severity,
            "",
            "PRIORITY",
            self.priority,
            "",
            "IMMEDIATE ACTIONS",
            *(f"  {index}. {item}" for index, item in enumerate(self.immediate_actions, start=1)),
            "",
            "RECOMMENDED RESOURCES",
            *(f"  - {item}" for item in self.recommended_resources),
            "",
            "RISK FACTORS",
            *(f"  - {item}" for item in self.risk_factors),
            "",
            "OPERATIONAL NOTES",
            *(f"  - {item}" for item in self.operational_notes),
        ]
        return "\n".join(sections)


class DetectionBoxSchema(BaseModel):
    """One detection with its frame-relative box, for overlay rendering."""

    detection_class: str
    confidence: float
    x1: float | None = None
    y1: float | None = None
    x2: float | None = None
    y2: float | None = None


class SceneSchema(BaseModel):
    """The detections behind an analysis, with frame geometry for scaling overlays."""

    detections: list[DetectionBoxSchema] = Field(default_factory=list)
    discarded_count: int = 0
    frame_width: int | None = None
    frame_height: int | None = None


class IncidentAnalysisResponse(BaseModel):
    """The primary ARES response: one image analysed into a complete command picture."""

    incident: IncidentResponseSchema
    assessment: IncidentAssessment
    decision: DecisionResult
    resources: AllocationResult
    commander_brief: CommanderBrief
    scene: SceneSchema
    timestamp: datetime


class IncidentAnalysisRecordSchema(ORMResponseSchema):
    """One persisted analysis revision within an incident's history."""

    id: UUID
    incident_id: UUID
    revision: int
    severity_level: str
    severity_score: float
    priority_level: str
    priority_score: float
    confidence: float
    assessment: dict
    decision: dict
    resources: dict
    commander_brief: dict
    created_at: datetime


class IncidentTimelineResponse(BaseModel):
    """An incident with every analysis revision recorded against it, oldest first."""

    incident: IncidentResponseSchema
    revisions: list[IncidentAnalysisRecordSchema] = Field(default_factory=list)


class IncidentSummarySchema(BaseModel):
    """A compact incident row for the operations feed, with its latest grading."""

    id: UUID
    title: str
    incident_type: str
    status: str
    priority: str
    location: str
    latitude: float | None = None
    longitude: float | None = None
    severity_level: str | None = None
    severity_score: float | None = None
    priority_score: float | None = None
    confidence: float | None = None
    revision_count: int = 0
    created_at: datetime
    updated_at: datetime


class IncidentListResponse(BaseModel):
    """A page of incidents, newest first."""

    incidents: list[IncidentSummarySchema] = Field(default_factory=list)
    total: int = 0


class ResourceInventoryItemSchema(BaseModel):
    """Standing stock for one resource kind, with live commitment against it."""

    resource_kind: str
    label: str
    total: int = 0
    available: int = 0
    unavailable: int = 0
    resource_names: list[str] = Field(default_factory=list)


class ResourceInventoryResponse(BaseModel):
    """The full resource pool, grouped by kind."""

    items: list[ResourceInventoryItemSchema] = Field(default_factory=list)
    total_units: int = 0
    available_units: int = 0
    unrecognised_types: list[str] = Field(default_factory=list)


class ComponentHealthSchema(BaseModel):
    """Readiness of one backend subsystem."""

    component: str
    label: str
    status: str
    detail: str


class SystemStatusResponse(BaseModel):
    """Per-subsystem readiness for the operations status board."""

    status: str
    version: str
    environment: str
    components: list[ComponentHealthSchema] = Field(default_factory=list)
    checked_at: datetime
