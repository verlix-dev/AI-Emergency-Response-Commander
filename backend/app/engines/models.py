"""Typed input and output contracts for the Decision Intelligence Engine."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DisasterType(str, Enum):
    """Disaster taxonomy the reasoning rules are calibrated against."""

    BUILDING_FIRE = "BUILDING_FIRE"
    FLOOD = "FLOOD"
    ROAD_ACCIDENT = "ROAD_ACCIDENT"
    EARTHQUAKE = "EARTHQUAKE"
    BUILDING_COLLAPSE = "BUILDING_COLLAPSE"
    CHEMICAL_LEAK = "CHEMICAL_LEAK"
    TRAIN_ACCIDENT = "TRAIN_ACCIDENT"
    CYCLONE_STORM = "CYCLONE_STORM"
    LANDSLIDE = "LANDSLIDE"
    UNKNOWN = "UNKNOWN"


class SeverityLevel(str, Enum):
    """How much harm the incident presents right now."""

    MINOR = "MINOR"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"
    CRITICAL = "CRITICAL"


class PriorityLevel(str, Enum):
    """How fast the incident must be answered, independent of severity."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    URGENT = "URGENT"
    CRITICAL = "CRITICAL"


class ConfidenceLevel(str, Enum):
    """How much of the evidence needed for the decision is actually present."""

    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class Weather(str, Enum):
    """Normalized weather conditions affecting access and hazard behaviour."""

    CLEAR = "CLEAR"
    RAIN = "RAIN"
    STORM = "STORM"
    FOG = "FOG"
    SNOW = "SNOW"
    EXTREME_HEAT = "EXTREME_HEAT"
    WIND = "WIND"
    UNKNOWN = "UNKNOWN"


class IncidentAssessment(BaseModel):
    """Structured observations describing a single emergency.

    Every field except ``incident_type`` is optional and defaults to ``None``. ``None`` means
    "not reported" and is deliberately distinct from ``0`` or ``False``, which mean "reported
    as absent". The confidence engine relies on that distinction, so unknown values must never
    be defaulted to a concrete number. Unknown keys are rejected rather than ignored: a
    misspelled life-safety field must fail loudly instead of silently vanishing.
    """

    model_config = ConfigDict(extra="forbid")

    incident_type: str = Field(min_length=1, max_length=100)
    victims: int | None = Field(default=None, ge=0)
    children: int | None = Field(default=None, ge=0)
    elderly: int | None = Field(default=None, ge=0)
    trapped_people: int | None = Field(default=None, ge=0)
    people_detected: int | None = Field(default=None, ge=0)
    passengers_onboard: int | None = Field(default=None, ge=0)
    responders_on_scene: int | None = Field(default=None, ge=0)
    fire_detected: bool | None = None
    smoke_detected: bool | None = None
    collapsed_structure: bool | None = None
    structural_damage: bool | None = None
    hazardous_material: bool | None = None
    toxic_gas_detected: bool | None = None
    explosion_risk: bool | None = None
    gas_station_nearby: bool | None = None
    power_lines_down: bool | None = None
    derailment: bool | None = None
    road_blocked: bool | None = None
    evacuation_required: bool | None = None
    night_time: bool | None = None
    water_level_m: float | None = Field(default=None, ge=0.0, le=30.0)
    wind_speed_kmh: float | None = Field(default=None, ge=0.0, le=400.0)
    hospital_distance_km: float | None = Field(default=None, ge=0.0, le=2000.0)
    weather: str | None = Field(default=None, max_length=50)


class ReasoningFactor(BaseModel):
    """One rule evaluation that changed a score, retained for traceability."""

    code: str
    description: str
    contribution: float


class SeverityResult(BaseModel):
    """Present-tense harm assessment."""

    score: float
    level: SeverityLevel
    factors: list[ReasoningFactor]
    applied_floor: str | None = None


class PriorityResult(BaseModel):
    """Response urgency assessment, computed independently of severity."""

    score: float
    level: PriorityLevel
    factors: list[ReasoningFactor]
    applied_floor: str | None = None


class ConfidenceResult(BaseModel):
    """Evidence-coverage assessment for the decision as a whole."""

    confidence: float
    level: ConfidenceLevel
    observed_fields: list[str]
    missing_fields: list[str]
    penalties: list[ReasoningFactor]
    applied_cap: str | None = None


class Explanation(BaseModel):
    """Deterministic, template-rendered account of the decision."""

    current_situation: str
    severity: str
    priority: str
    key_risk_factors: list[str]
    recommended_immediate_actions: list[str]
    reasoning_summary: str


class DecisionResult(BaseModel):
    """Complete output of one Decision Intelligence Engine run."""

    incident_type: str
    disaster_type: DisasterType
    severity_score: float
    severity_level: SeverityLevel
    priority_score: float
    priority_level: PriorityLevel
    confidence: float
    confidence_level: ConfidenceLevel
    recommended_actions: list[str]
    risk_factors: list[str]
    summary: str
    explanation: Explanation
    severity_detail: SeverityResult
    priority_detail: PriorityResult
    confidence_detail: ConfidenceResult
