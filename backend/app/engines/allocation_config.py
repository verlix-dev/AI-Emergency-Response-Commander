"""Configurable allocation rules, ratios, and caps.

Every quantity the allocation engine can produce originates here, so tuning the response
posture is a change to this module rather than to allocation logic. Rules are data: each
declares what triggers it, what it asks for, and why.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from app.engines.allocation_models import AllocationPriority, ResourceKind
from app.engines.models import DisasterType, IncidentAssessment, SeverityLevel

# Per-unit workload ratios. A ratio of 4 means one unit is requested per 4 people, rounded up.
VICTIMS_PER_AMBULANCE = 2
VICTIMS_PER_MEDICAL_TEAM = 6
TRAPPED_PER_RESCUE_TEAM = 3
PASSENGERS_PER_MEDICAL_TEAM = 25
EXPOSED_PER_POLICE_UNIT = 40

# Absolute ceilings, preventing a single large incident from requesting an implausible fleet.
MAX_UNITS_PER_KIND = 12
MAX_TOTAL_UNITS = 40

# Severity levels at which a baseline command presence is warranted.
POLICE_BASELINE_SEVERITY = SeverityLevel.MODERATE
MEDICAL_BASELINE_SEVERITY = SeverityLevel.HIGH

# Fire-truck escalation by severity, applied when fire is confirmed.
FIRE_TRUCKS_BY_SEVERITY: dict[SeverityLevel, int] = {
    SeverityLevel.MINOR: 1,
    SeverityLevel.MODERATE: 2,
    SeverityLevel.HIGH: 3,
    SeverityLevel.SEVERE: 4,
    SeverityLevel.CRITICAL: 6,
}

# Water depth beyond which boats replace road access for rescue.
BOAT_REQUIRED_WATER_DEPTH_M = 0.5
BOATS_PER_TRAPPED_GROUP = 4


@dataclass(frozen=True)
class AllocationRule:
    """A single deterministic requirement, evaluated against one assessment."""

    rule_id: str
    resource_kind: ResourceKind
    priority: AllocationPriority
    reason: str
    applies: Callable[[IncidentAssessment, SeverityLevel], bool]
    quantity: Callable[[IncidentAssessment, SeverityLevel], int]
    disaster_types: frozenset[DisasterType] = field(default_factory=frozenset)


def _ceil_ratio(count: int | None, per_unit: int) -> int:
    """Return units needed to cover a count at the given ratio, rounded up."""
    if not count or per_unit <= 0:
        return 0
    return -(-count // per_unit)


def _severity_at_least(level: SeverityLevel, minimum: SeverityLevel) -> bool:
    """Return whether a severity level meets or exceeds a minimum."""
    order = list(SeverityLevel)
    return order.index(level) >= order.index(minimum)


def _exposed_count(assessment: IncidentAssessment) -> int:
    """Return people detected beyond those already counted as casualties."""
    if assessment.people_detected is None:
        return 0
    return max(0, assessment.people_detected - (assessment.victims or 0))


ALLOCATION_RULES: tuple[AllocationRule, ...] = (
    AllocationRule(
        rule_id="ALLOC.FIRE.01",
        resource_kind=ResourceKind.FIRE_TRUCK,
        priority=AllocationPriority.CRITICAL,
        reason="Active fire requires suppression crews scaled to incident severity.",
        applies=lambda assessment, severity: bool(assessment.fire_detected),
        quantity=lambda assessment, severity: FIRE_TRUCKS_BY_SEVERITY[severity],
    ),
    AllocationRule(
        rule_id="ALLOC.FIRE.02",
        resource_kind=ResourceKind.FIRE_TRUCK,
        priority=AllocationPriority.HIGH,
        reason="Smoke without confirmed flame still requires a suppression capability on scene.",
        applies=lambda assessment, severity: bool(assessment.smoke_detected)
        and not assessment.fire_detected,
        quantity=lambda assessment, severity: 1,
    ),
    AllocationRule(
        rule_id="ALLOC.FIRE.03",
        resource_kind=ResourceKind.FIRE_TRUCK,
        priority=AllocationPriority.CRITICAL,
        reason="Fuel storage near an active fire requires additional cooling capability.",
        applies=lambda assessment, severity: bool(
            assessment.gas_station_nearby and (assessment.fire_detected or assessment.explosion_risk)
        ),
        quantity=lambda assessment, severity: 2,
    ),
    AllocationRule(
        rule_id="ALLOC.MED.01",
        resource_kind=ResourceKind.AMBULANCE,
        priority=AllocationPriority.CRITICAL,
        reason="Casualty transport scaled to the reported casualty count.",
        applies=lambda assessment, severity: bool(assessment.victims),
        quantity=lambda assessment, severity: _ceil_ratio(
            assessment.victims, VICTIMS_PER_AMBULANCE
        ),
    ),
    AllocationRule(
        rule_id="ALLOC.MED.02",
        resource_kind=ResourceKind.AMBULANCE,
        priority=AllocationPriority.CRITICAL,
        reason="Trapped casualties require transport standing by for the moment of release.",
        applies=lambda assessment, severity: bool(assessment.trapped_people),
        quantity=lambda assessment, severity: _ceil_ratio(
            assessment.trapped_people, VICTIMS_PER_AMBULANCE
        ),
    ),
    AllocationRule(
        rule_id="ALLOC.MED.03",
        resource_kind=ResourceKind.AMBULANCE,
        priority=AllocationPriority.MEDIUM,
        reason="Precautionary transport for a serious incident with no confirmed casualties.",
        applies=lambda assessment, severity: not assessment.victims
        and not assessment.trapped_people
        and _severity_at_least(severity, MEDICAL_BASELINE_SEVERITY),
        quantity=lambda assessment, severity: 1,
    ),
    AllocationRule(
        rule_id="ALLOC.MED.04",
        resource_kind=ResourceKind.MEDICAL_TEAM,
        priority=AllocationPriority.HIGH,
        reason="On-scene triage capability for multiple casualties.",
        applies=lambda assessment, severity: bool(assessment.victims),
        quantity=lambda assessment, severity: _ceil_ratio(
            assessment.victims, VICTIMS_PER_MEDICAL_TEAM
        ),
    ),
    AllocationRule(
        rule_id="ALLOC.MED.05",
        resource_kind=ResourceKind.MEDICAL_TEAM,
        priority=AllocationPriority.HIGH,
        reason="Mass-casualty triage for the passenger load involved.",
        applies=lambda assessment, severity: bool(assessment.passengers_onboard),
        quantity=lambda assessment, severity: _ceil_ratio(
            assessment.passengers_onboard, PASSENGERS_PER_MEDICAL_TEAM
        ),
    ),
    AllocationRule(
        rule_id="ALLOC.MED.06",
        resource_kind=ResourceKind.MEDICAL_TEAM,
        priority=AllocationPriority.HIGH,
        reason="Vulnerable occupants require assisted medical handling.",
        applies=lambda assessment, severity: bool(assessment.children or assessment.elderly),
        quantity=lambda assessment, severity: 1,
    ),
    AllocationRule(
        rule_id="ALLOC.SAR.01",
        resource_kind=ResourceKind.SEARCH_RESCUE,
        priority=AllocationPriority.CRITICAL,
        reason="Technical rescue for people trapped and awaiting extraction.",
        applies=lambda assessment, severity: bool(assessment.trapped_people),
        quantity=lambda assessment, severity: _ceil_ratio(
            assessment.trapped_people, TRAPPED_PER_RESCUE_TEAM
        ),
    ),
    AllocationRule(
        rule_id="ALLOC.SAR.02",
        resource_kind=ResourceKind.SEARCH_RESCUE,
        priority=AllocationPriority.CRITICAL,
        reason="Structural collapse requires urban search and rescue with void search capability.",
        applies=lambda assessment, severity: bool(assessment.collapsed_structure),
        quantity=lambda assessment, severity: 2,
    ),
    AllocationRule(
        rule_id="ALLOC.SAR.03",
        resource_kind=ResourceKind.SEARCH_RESCUE,
        priority=AllocationPriority.HIGH,
        reason="Unaccounted people in the affected area require a search capability.",
        applies=lambda assessment, severity: _exposed_count(assessment) > 0
        and _severity_at_least(severity, SeverityLevel.SEVERE),
        quantity=lambda assessment, severity: 1,
    ),
    AllocationRule(
        rule_id="ALLOC.BOAT.01",
        resource_kind=ResourceKind.BOAT,
        priority=AllocationPriority.CRITICAL,
        reason="Water depth prevents road-vehicle access; rescue craft are required.",
        applies=lambda assessment, severity: (assessment.water_level_m or 0.0)
        >= BOAT_REQUIRED_WATER_DEPTH_M,
        quantity=lambda assessment, severity: max(
            1,
            _ceil_ratio(
                (assessment.trapped_people or 0) + _exposed_count(assessment),
                BOATS_PER_TRAPPED_GROUP,
            ),
        ),
    ),
    AllocationRule(
        rule_id="ALLOC.BOAT.02",
        resource_kind=ResourceKind.BOAT,
        priority=AllocationPriority.HIGH,
        reason="A dedicated safety boat is mandatory whenever crews work on water.",
        applies=lambda assessment, severity: (assessment.water_level_m or 0.0)
        >= BOAT_REQUIRED_WATER_DEPTH_M,
        quantity=lambda assessment, severity: 1,
    ),
    AllocationRule(
        rule_id="ALLOC.HAZ.01",
        resource_kind=ResourceKind.HAZMAT,
        priority=AllocationPriority.CRITICAL,
        reason="Toxic release requires hazmat entry, detection, and decontamination.",
        applies=lambda assessment, severity: bool(assessment.toxic_gas_detected),
        quantity=lambda assessment, severity: 2,
    ),
    AllocationRule(
        rule_id="ALLOC.HAZ.02",
        resource_kind=ResourceKind.HAZMAT,
        priority=AllocationPriority.CRITICAL,
        reason="Hazardous material on scene requires specialist identification and control.",
        applies=lambda assessment, severity: bool(assessment.hazardous_material),
        quantity=lambda assessment, severity: 1,
    ),
    AllocationRule(
        rule_id="ALLOC.HAZ.03",
        resource_kind=ResourceKind.HAZMAT,
        priority=AllocationPriority.CRITICAL,
        reason="Explosion risk requires specialist assessment before any crew commitment.",
        applies=lambda assessment, severity: bool(assessment.explosion_risk),
        quantity=lambda assessment, severity: 1,
    ),
    AllocationRule(
        rule_id="ALLOC.HEAVY.01",
        resource_kind=ResourceKind.HEAVY_MACHINERY,
        priority=AllocationPriority.HIGH,
        reason="Debris removal and controlled lifting at a collapsed structure.",
        applies=lambda assessment, severity: bool(assessment.collapsed_structure),
        quantity=lambda assessment, severity: 2,
    ),
    AllocationRule(
        rule_id="ALLOC.HEAVY.02",
        resource_kind=ResourceKind.HEAVY_MACHINERY,
        priority=AllocationPriority.MEDIUM,
        reason="Blocked access requires clearance plant to open a route.",
        applies=lambda assessment, severity: bool(assessment.road_blocked),
        quantity=lambda assessment, severity: 1,
    ),
    AllocationRule(
        rule_id="ALLOC.HEAVY.03",
        resource_kind=ResourceKind.HEAVY_MACHINERY,
        priority=AllocationPriority.HIGH,
        reason="Derailed rolling stock requires heavy lifting capability.",
        applies=lambda assessment, severity: bool(assessment.derailment),
        quantity=lambda assessment, severity: 1,
    ),
    AllocationRule(
        rule_id="ALLOC.POL.01",
        resource_kind=ResourceKind.POLICE,
        priority=AllocationPriority.HIGH,
        reason="Scene cordon and traffic control for an incident of this severity.",
        applies=lambda assessment, severity: _severity_at_least(
            severity, POLICE_BASELINE_SEVERITY
        ),
        quantity=lambda assessment, severity: 2,
    ),
    AllocationRule(
        rule_id="ALLOC.POL.02",
        resource_kind=ResourceKind.POLICE,
        priority=AllocationPriority.HIGH,
        reason="Crowd management scaled to the number of people in the affected area.",
        applies=lambda assessment, severity: _exposed_count(assessment) > 0,
        quantity=lambda assessment, severity: _ceil_ratio(
            _exposed_count(assessment), EXPOSED_PER_POLICE_UNIT
        ),
    ),
    AllocationRule(
        rule_id="ALLOC.POL.03",
        resource_kind=ResourceKind.POLICE,
        priority=AllocationPriority.CRITICAL,
        reason="Evacuation and withdrawal perimeter enforcement.",
        applies=lambda assessment, severity: bool(
            assessment.evacuation_required or assessment.toxic_gas_detected
            or assessment.explosion_risk
        ),
        quantity=lambda assessment, severity: 3,
    ),
    AllocationRule(
        rule_id="ALLOC.POL.04",
        resource_kind=ResourceKind.POLICE,
        priority=AllocationPriority.MEDIUM,
        reason="Downed power infrastructure requires public exclusion until isolation.",
        applies=lambda assessment, severity: bool(assessment.power_lines_down),
        quantity=lambda assessment, severity: 1,
    ),
)

RESOURCE_TYPE_ALIASES: dict[str, ResourceKind] = {
    "fire_truck": ResourceKind.FIRE_TRUCK,
    "firetruck": ResourceKind.FIRE_TRUCK,
    "fire_engine": ResourceKind.FIRE_TRUCK,
    "pumper": ResourceKind.FIRE_TRUCK,
    "ambulance": ResourceKind.AMBULANCE,
    "ems": ResourceKind.AMBULANCE,
    "police": ResourceKind.POLICE,
    "police_unit": ResourceKind.POLICE,
    "patrol": ResourceKind.POLICE,
    "search_rescue": ResourceKind.SEARCH_RESCUE,
    "search_and_rescue": ResourceKind.SEARCH_RESCUE,
    "sar": ResourceKind.SEARCH_RESCUE,
    "usar": ResourceKind.SEARCH_RESCUE,
    "rescue_team": ResourceKind.SEARCH_RESCUE,
    "boat": ResourceKind.BOAT,
    "rescue_boat": ResourceKind.BOAT,
    "watercraft": ResourceKind.BOAT,
    "medical_team": ResourceKind.MEDICAL_TEAM,
    "medical": ResourceKind.MEDICAL_TEAM,
    "triage_team": ResourceKind.MEDICAL_TEAM,
    "hazmat": ResourceKind.HAZMAT,
    "hazmat_unit": ResourceKind.HAZMAT,
    "chemical_response": ResourceKind.HAZMAT,
    "heavy_machinery": ResourceKind.HEAVY_MACHINERY,
    "heavy_plant": ResourceKind.HEAVY_MACHINERY,
    "crane": ResourceKind.HEAVY_MACHINERY,
    "excavator": ResourceKind.HEAVY_MACHINERY,
    "bulldozer": ResourceKind.HEAVY_MACHINERY,
}

PRIORITY_ORDER: tuple[AllocationPriority, ...] = (
    AllocationPriority.CRITICAL,
    AllocationPriority.HIGH,
    AllocationPriority.MEDIUM,
    AllocationPriority.LOW,
)

RESOURCE_KIND_ORDER: tuple[ResourceKind, ...] = (
    ResourceKind.FIRE_TRUCK,
    ResourceKind.AMBULANCE,
    ResourceKind.SEARCH_RESCUE,
    ResourceKind.HAZMAT,
    ResourceKind.MEDICAL_TEAM,
    ResourceKind.BOAT,
    ResourceKind.HEAVY_MACHINERY,
    ResourceKind.POLICE,
)
