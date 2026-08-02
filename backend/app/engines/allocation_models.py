"""Typed contracts for deterministic resource allocation."""

from enum import Enum

from pydantic import BaseModel, Field


class ResourceKind(str, Enum):
    """Resource categories the allocation engine can recommend."""

    FIRE_TRUCK = "FIRE_TRUCK"
    AMBULANCE = "AMBULANCE"
    POLICE = "POLICE"
    SEARCH_RESCUE = "SEARCH_RESCUE"
    BOAT = "BOAT"
    MEDICAL_TEAM = "MEDICAL_TEAM"
    HAZMAT = "HAZMAT"
    HEAVY_MACHINERY = "HEAVY_MACHINERY"


class AllocationPriority(str, Enum):
    """How essential a recommended resource is to a safe response."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ResourceRecommendation(BaseModel):
    """One resource requirement, with what backs it and what can be met."""

    resource_kind: ResourceKind
    quantity: int = Field(ge=0)
    priority: AllocationPriority
    reason: str
    rule_ids: list[str]
    fulfilled_quantity: int = Field(default=0, ge=0)
    shortfall: int = Field(default=0, ge=0)
    assigned_resource_names: list[str] = Field(default_factory=list)


class AllocationResult(BaseModel):
    """The complete set of resource requirements derived from a decision."""

    recommendations: list[ResourceRecommendation]
    total_units_requested: int = Field(ge=0)
    total_units_fulfilled: int = Field(ge=0)
    unmet_requirements: list[str] = Field(default_factory=list)
