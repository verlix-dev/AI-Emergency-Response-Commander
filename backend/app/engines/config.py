"""Deterministic thresholds, weights, and rule tables for the Decision Intelligence Engine.

Every tunable value used by the engines is defined here so that recalibration never requires
editing reasoning logic. Engines contain rules; this module contains numbers and text.
"""

from dataclasses import dataclass

from app.engines.models import (
    ConfidenceLevel,
    DisasterType,
    PriorityLevel,
    SeverityLevel,
    Weather,
)

SCORE_MIN = 0.0
SCORE_MAX = 100.0
SCORE_PRECISION = 1

CONFIDENCE_MIN = 0.0
CONFIDENCE_MAX = 1.0
CONFIDENCE_PRECISION = 3

MAX_LISTED_RISK_FACTORS = 8
MAX_LISTED_ACTIONS = 8

SEVERITY_BANDS: tuple[tuple[float, SeverityLevel], ...] = (
    (85.0, SeverityLevel.CRITICAL),
    (65.0, SeverityLevel.SEVERE),
    (40.0, SeverityLevel.HIGH),
    (20.0, SeverityLevel.MODERATE),
    (0.0, SeverityLevel.MINOR),
)

PRIORITY_BANDS: tuple[tuple[float, PriorityLevel], ...] = (
    (85.0, PriorityLevel.CRITICAL),
    (65.0, PriorityLevel.URGENT),
    (40.0, PriorityLevel.HIGH),
    (20.0, PriorityLevel.MODERATE),
    (0.0, PriorityLevel.LOW),
)

CONFIDENCE_BANDS: tuple[tuple[float, ConfidenceLevel], ...] = (
    (0.80, ConfidenceLevel.HIGH),
    (0.60, ConfidenceLevel.MODERATE),
    (0.40, ConfidenceLevel.LOW),
    (0.00, ConfidenceLevel.VERY_LOW),
)

DISASTER_TYPE_ALIASES: dict[str, DisasterType] = {
    "building_fire": DisasterType.BUILDING_FIRE,
    "fire": DisasterType.BUILDING_FIRE,
    "structure_fire": DisasterType.BUILDING_FIRE,
    "house_fire": DisasterType.BUILDING_FIRE,
    "flood": DisasterType.FLOOD,
    "flooding": DisasterType.FLOOD,
    "flash_flood": DisasterType.FLOOD,
    "road_accident": DisasterType.ROAD_ACCIDENT,
    "road_traffic_accident": DisasterType.ROAD_ACCIDENT,
    "traffic_accident": DisasterType.ROAD_ACCIDENT,
    "vehicle_accident": DisasterType.ROAD_ACCIDENT,
    "earthquake": DisasterType.EARTHQUAKE,
    "seismic_event": DisasterType.EARTHQUAKE,
    "building_collapse": DisasterType.BUILDING_COLLAPSE,
    "collapse": DisasterType.BUILDING_COLLAPSE,
    "structural_collapse": DisasterType.BUILDING_COLLAPSE,
    "chemical_leak": DisasterType.CHEMICAL_LEAK,
    "gas_leak": DisasterType.CHEMICAL_LEAK,
    "chemical_gas_leak": DisasterType.CHEMICAL_LEAK,
    "chemical_spill": DisasterType.CHEMICAL_LEAK,
    "hazmat": DisasterType.CHEMICAL_LEAK,
    "train_accident": DisasterType.TRAIN_ACCIDENT,
    "train_derailment": DisasterType.TRAIN_ACCIDENT,
    "rail_accident": DisasterType.TRAIN_ACCIDENT,
    "cyclone": DisasterType.CYCLONE_STORM,
    "cyclone_storm": DisasterType.CYCLONE_STORM,
    "storm": DisasterType.CYCLONE_STORM,
    "hurricane": DisasterType.CYCLONE_STORM,
    "typhoon": DisasterType.CYCLONE_STORM,
    "landslide": DisasterType.LANDSLIDE,
    "mudslide": DisasterType.LANDSLIDE,
    "rockslide": DisasterType.LANDSLIDE,
}

WEATHER_ALIASES: dict[str, Weather] = {
    "clear": Weather.CLEAR,
    "sunny": Weather.CLEAR,
    "fair": Weather.CLEAR,
    "rain": Weather.RAIN,
    "rainy": Weather.RAIN,
    "drizzle": Weather.RAIN,
    "storm": Weather.STORM,
    "stormy": Weather.STORM,
    "thunderstorm": Weather.STORM,
    "fog": Weather.FOG,
    "foggy": Weather.FOG,
    "mist": Weather.FOG,
    "snow": Weather.SNOW,
    "snowy": Weather.SNOW,
    "blizzard": Weather.SNOW,
    "extreme_heat": Weather.EXTREME_HEAT,
    "heat": Weather.EXTREME_HEAT,
    "heatwave": Weather.EXTREME_HEAT,
    "wind": Weather.WIND,
    "windy": Weather.WIND,
}


@dataclass(frozen=True)
class SeverityWeights:
    """Points contributed by each severity rule, and the caps that bound them."""

    victim_points: float = 3.0
    victim_cap: float = 30.0
    child_points: float = 2.5
    child_cap: float = 10.0
    elderly_points: float = 2.0
    elderly_cap: float = 8.0
    trapped_points: float = 5.0
    trapped_cap: float = 20.0
    exposed_points: float = 0.5
    exposed_cap: float = 8.0
    passenger_points: float = 0.08
    passenger_cap: float = 12.0
    fire: float = 10.0
    smoke: float = 5.0
    collapsed_structure: float = 15.0
    structural_damage: float = 8.0
    hazardous_material: float = 12.0
    toxic_gas: float = 14.0
    explosion_risk: float = 15.0
    derailment: float = 10.0
    power_lines_down: float = 5.0
    road_blocked: float = 6.0
    night_time: float = 3.0
    gas_station_with_fire: float = 8.0
    gas_station_without_fire: float = 3.0
    collapse_entrapment: float = 10.0
    downwind_exposure: float = 8.0
    emphasis_multiplier: float = 1.3


@dataclass(frozen=True)
class PriorityWeights:
    """Points contributed by each urgency rule, and the caps that bound them."""

    trapped_points: float = 8.0
    trapped_cap: float = 30.0
    victim_points: float = 1.5
    victim_cap: float = 20.0
    child_points: float = 2.0
    child_cap: float = 8.0
    elderly_points: float = 1.5
    elderly_cap: float = 6.0
    toxic_gas: float = 25.0
    explosion_risk: float = 25.0
    hazardous_material: float = 18.0
    collapsed_structure: float = 20.0
    fire: float = 15.0
    smoke: float = 5.0
    derailment: float = 12.0
    rising_water: float = 15.0
    power_lines_down: float = 6.0
    road_blocked: float = 10.0
    night_time: float = 3.0
    evacuation_required: float = 8.0
    responders_present_relief: float = -6.0


@dataclass(frozen=True)
class ConfidenceWeights:
    """Evidence weights and the penalties applied for inconsistent reporting."""

    critical_field_weight: int = 3
    significant_field_weight: int = 2
    refining_field_weight: int = 1
    unknown_type_cap: float = 0.55
    missing_critical_cap: float = 0.70
    contradiction_penalty: float = 0.10
    inconsistency_penalty: float = 0.08


SEVERITY_WEIGHTS = SeverityWeights()
PRIORITY_WEIGHTS = PriorityWeights()
CONFIDENCE_WEIGHTS = ConfidenceWeights()

WATER_DEPTH_SEVERITY_BANDS: tuple[tuple[float, float], ...] = (
    (2.0, 16.0),
    (1.0, 12.0),
    (0.5, 8.0),
    (0.01, 4.0),
)

HOSPITAL_DISTANCE_SEVERITY_BANDS: tuple[tuple[float, float], ...] = (
    (20.0, 8.0),
    (10.0, 6.0),
    (5.0, 4.0),
    (2.0, 2.0),
)

HOSPITAL_DISTANCE_PRIORITY_BANDS: tuple[tuple[float, float], ...] = (
    (10.0, 8.0),
    (5.0, 5.0),
)

WIND_SPEED_SEVERITY_BANDS: tuple[tuple[float, float], ...] = (
    (60.0, 5.0),
    (40.0, 3.0),
)

WEATHER_SEVERITY_POINTS: dict[Weather, float] = {
    Weather.CLEAR: 0.0,
    Weather.RAIN: 3.0,
    Weather.STORM: 6.0,
    Weather.FOG: 4.0,
    Weather.SNOW: 5.0,
    Weather.EXTREME_HEAT: 4.0,
    Weather.WIND: 4.0,
    Weather.UNKNOWN: 0.0,
}

WEATHER_PRIORITY_POINTS: dict[Weather, float] = {
    Weather.CLEAR: 0.0,
    Weather.RAIN: 2.0,
    Weather.STORM: 6.0,
    Weather.FOG: 6.0,
    Weather.SNOW: 4.0,
    Weather.EXTREME_HEAT: 3.0,
    Weather.WIND: 3.0,
    Weather.UNKNOWN: 0.0,
}

RISING_WATER_THRESHOLD_M = 1.0
MASS_CASUALTY_VICTIM_THRESHOLD = 10
MAJOR_CASUALTY_VICTIM_THRESHOLD = 25

SEVERITY_FLOOR_TRAPPED = 65.0
SEVERITY_FLOOR_COLLAPSE_WITH_CASUALTIES = 65.0
SEVERITY_FLOOR_MASS_CASUALTY = 65.0
SEVERITY_FLOOR_MAJOR_CASUALTY = 85.0

PRIORITY_FLOOR_TRAPPED = 85.0
PRIORITY_FLOOR_TOXIC_GAS = 85.0
PRIORITY_FLOOR_EXPLOSION_RISK = 85.0
PRIORITY_FLOOR_HAZMAT_EXPOSURE = 80.0
PRIORITY_FLOOR_MASS_CASUALTY_FIRE = 80.0

FIELD_EVIDENCE_WEIGHTS: dict[str, int] = {
    "victims": 3,
    "trapped_people": 3,
    "people_detected": 3,
    "fire_detected": 3,
    "collapsed_structure": 3,
    "hazardous_material": 3,
    "toxic_gas_detected": 3,
    "water_level_m": 3,
    "passengers_onboard": 3,
    "children": 2,
    "elderly": 2,
    "smoke_detected": 2,
    "structural_damage": 2,
    "explosion_risk": 2,
    "derailment": 2,
    "road_blocked": 2,
    "hospital_distance_km": 2,
    "gas_station_nearby": 2,
    "power_lines_down": 1,
    "wind_speed_kmh": 1,
    "weather": 1,
    "night_time": 1,
    "responders_on_scene": 1,
    "evacuation_required": 1,
}

COMMON_EXPECTED_FIELDS: tuple[str, ...] = (
    "victims",
    "children",
    "elderly",
    "trapped_people",
    "people_detected",
    "road_blocked",
    "hospital_distance_km",
    "weather",
    "night_time",
    "responders_on_scene",
)


@dataclass(frozen=True)
class DisasterProfile:
    """Per-disaster calibration: baseline scores, emphasis, and expected evidence."""

    disaster_type: DisasterType
    severity_base: float
    urgency_bias: float
    extra_expected_fields: tuple[str, ...]
    critical_fields: tuple[str, ...]
    emphasised_factors: tuple[str, ...]

    @property
    def expected_fields(self) -> tuple[str, ...]:
        """Return every field the confidence engine expects for this disaster type."""
        merged = list(COMMON_EXPECTED_FIELDS)
        merged.extend(field for field in self.extra_expected_fields if field not in merged)
        return tuple(merged)


DISASTER_PROFILES: dict[DisasterType, DisasterProfile] = {
    DisasterType.BUILDING_FIRE: DisasterProfile(
        disaster_type=DisasterType.BUILDING_FIRE,
        severity_base=8.0,
        urgency_bias=12.0,
        extra_expected_fields=(
            "fire_detected",
            "smoke_detected",
            "structural_damage",
            "gas_station_nearby",
            "explosion_risk",
        ),
        critical_fields=("victims", "trapped_people", "fire_detected"),
        emphasised_factors=("HAZARD_FIRE", "HAZARD_SMOKE"),
    ),
    DisasterType.FLOOD: DisasterProfile(
        disaster_type=DisasterType.FLOOD,
        severity_base=6.0,
        urgency_bias=8.0,
        extra_expected_fields=(
            "water_level_m",
            "power_lines_down",
            "evacuation_required",
        ),
        critical_fields=("victims", "trapped_people", "water_level_m"),
        emphasised_factors=("HAZARD_WATER_DEPTH",),
    ),
    DisasterType.ROAD_ACCIDENT: DisasterProfile(
        disaster_type=DisasterType.ROAD_ACCIDENT,
        severity_base=4.0,
        urgency_bias=10.0,
        extra_expected_fields=("fire_detected", "hazardous_material"),
        critical_fields=("victims", "trapped_people"),
        emphasised_factors=(),
    ),
    DisasterType.EARTHQUAKE: DisasterProfile(
        disaster_type=DisasterType.EARTHQUAKE,
        severity_base=12.0,
        urgency_bias=18.0,
        extra_expected_fields=(
            "collapsed_structure",
            "structural_damage",
            "fire_detected",
            "power_lines_down",
        ),
        critical_fields=("victims", "trapped_people", "collapsed_structure"),
        emphasised_factors=("HAZARD_COLLAPSED_STRUCTURE", "HAZARD_STRUCTURAL_DAMAGE"),
    ),
    DisasterType.BUILDING_COLLAPSE: DisasterProfile(
        disaster_type=DisasterType.BUILDING_COLLAPSE,
        severity_base=12.0,
        urgency_bias=18.0,
        extra_expected_fields=(
            "collapsed_structure",
            "structural_damage",
            "hazardous_material",
        ),
        critical_fields=("victims", "trapped_people", "collapsed_structure"),
        emphasised_factors=("HAZARD_COLLAPSED_STRUCTURE",),
    ),
    DisasterType.CHEMICAL_LEAK: DisasterProfile(
        disaster_type=DisasterType.CHEMICAL_LEAK,
        severity_base=10.0,
        urgency_bias=25.0,
        extra_expected_fields=(
            "hazardous_material",
            "toxic_gas_detected",
            "explosion_risk",
            "wind_speed_kmh",
            "evacuation_required",
        ),
        critical_fields=("victims", "trapped_people", "toxic_gas_detected"),
        emphasised_factors=("HAZARD_TOXIC_GAS", "HAZARD_HAZARDOUS_MATERIAL"),
    ),
    DisasterType.TRAIN_ACCIDENT: DisasterProfile(
        disaster_type=DisasterType.TRAIN_ACCIDENT,
        severity_base=10.0,
        urgency_bias=15.0,
        extra_expected_fields=(
            "derailment",
            "passengers_onboard",
            "hazardous_material",
            "fire_detected",
        ),
        critical_fields=("victims", "trapped_people", "passengers_onboard"),
        emphasised_factors=("HAZARD_DERAILMENT",),
    ),
    DisasterType.CYCLONE_STORM: DisasterProfile(
        disaster_type=DisasterType.CYCLONE_STORM,
        severity_base=8.0,
        urgency_bias=6.0,
        extra_expected_fields=(
            "wind_speed_kmh",
            "water_level_m",
            "power_lines_down",
            "evacuation_required",
        ),
        critical_fields=("victims", "trapped_people"),
        emphasised_factors=("CONTEXT_WIND_SPEED",),
    ),
    DisasterType.LANDSLIDE: DisasterProfile(
        disaster_type=DisasterType.LANDSLIDE,
        severity_base=8.0,
        urgency_bias=12.0,
        extra_expected_fields=(
            "collapsed_structure",
            "structural_damage",
            "water_level_m",
        ),
        critical_fields=("victims", "trapped_people"),
        emphasised_factors=("HAZARD_COLLAPSED_STRUCTURE",),
    ),
    DisasterType.UNKNOWN: DisasterProfile(
        disaster_type=DisasterType.UNKNOWN,
        severity_base=5.0,
        urgency_bias=8.0,
        extra_expected_fields=(),
        critical_fields=("victims", "trapped_people"),
        emphasised_factors=(),
    ),
}


@dataclass(frozen=True)
class ActionTemplate:
    """One recommended action, rendered deterministically from decision context."""

    code: str
    rank: int
    template: str


BASELINE_ACTIONS: tuple[ActionTemplate, ...] = (
    ActionTemplate(
        code="ESTABLISH_COMMAND",
        rank=10,
        template="Establish incident command and confirm a single point of contact on scene.",
    ),
    ActionTemplate(
        code="CONFIRM_SCENE_SAFETY",
        rank=20,
        template="Confirm scene safety and hazard control before committing crews.",
    ),
)

CONDITIONAL_ACTIONS: tuple[ActionTemplate, ...] = (
    ActionTemplate(
        code="TECHNICAL_RESCUE",
        rank=30,
        template="Deploy technical rescue capability for {trapped_people} trapped casualties.",
    ),
    ActionTemplate(
        code="TOXIC_ZONE_CONTROL",
        rank=31,
        template=(
            "Establish hot, warm, and cold zones and evacuate downwind before any crew entry."
        ),
    ),
    ActionTemplate(
        code="EXPLOSION_WITHDRAWAL",
        rank=32,
        template="Enforce a withdrawal perimeter and apply cooling; treat explosion risk as live.",
    ),
    ActionTemplate(
        code="HAZMAT_IDENTIFY",
        rank=33,
        template="Request hazmat capability to identify the substance and set decontamination.",
    ),
    ActionTemplate(
        code="FIRE_ATTACK",
        rank=40,
        template="Commit fire crews with a confirmed water supply and a standby rescue crew.",
    ),
    ActionTemplate(
        code="STRUCTURAL_ASSESSMENT",
        rank=41,
        template="Request structural engineering assessment and shoring before entering voids.",
    ),
    ActionTemplate(
        code="WATER_RESCUE",
        rank=42,
        template="Deploy water rescue craft with a dedicated safety boat for isolated people.",
    ),
    ActionTemplate(
        code="RAIL_ISOLATION",
        rank=43,
        template="Confirm traction power isolation and line blockage before approaching rolling stock.",
    ),
    ActionTemplate(
        code="MASS_CASUALTY_TRIAGE",
        rank=50,
        template="Establish a casualty clearing station and triage {victims} reported casualties.",
    ),
    ActionTemplate(
        code="MEDICAL_TRANSPORT",
        rank=51,
        template="Alert receiving hospitals; nearest facility is {hospital_distance_km} km away.",
    ),
    ActionTemplate(
        code="VULNERABLE_OCCUPANTS",
        rank=52,
        template="Prioritise assisted evacuation for {children} children and {elderly} elderly.",
    ),
    ActionTemplate(
        code="EVACUATION",
        rank=53,
        template="Begin evacuation and confirm accounting for all people in the affected area.",
    ),
    ActionTemplate(
        code="ACCESS_ROUTE",
        rank=60,
        template="Task an alternative access route; the primary approach is reported blocked.",
    ),
    ActionTemplate(
        code="UTILITY_ISOLATION",
        rank=61,
        template="Request utility isolation for downed power infrastructure before entry.",
    ),
    ActionTemplate(
        code="IGNITION_CONTROL",
        rank=62,
        template="Remove ignition sources and protect nearby fuel storage.",
    ),
    ActionTemplate(
        code="WEATHER_MITIGATION",
        rank=63,
        template="Plan for degraded conditions: {weather} affects access, crews, and air assets.",
    ),
    ActionTemplate(
        code="VERIFY_INFORMATION",
        rank=70,
        template="Verify the incomplete picture on arrival; unreported detail is limiting confidence.",
    ),
)

RISK_FACTOR_FAMILY_PREFIXES: tuple[str, ...] = (
    "LIFE_",
    "URGENCY_",
    "HAZARD_",
    "ESCALATION_",
    "CONTEXT_",
    "FRICTION_",
)

RISK_SUBJECT_ALIASES: dict[str, str] = {
    "COLLAPSE": "COLLAPSED_STRUCTURE",
    "WATER_LEVEL": "WATER_DEPTH",
}

RISK_FACTOR_LABELS: dict[str, str] = {
    "LIFE_VICTIMS": "{victims} reported casualties",
    "LIFE_TRAPPED": "{trapped_people} people trapped and requiring rescue",
    "LIFE_CHILDREN": "{children} children among those affected",
    "LIFE_ELDERLY": "{elderly} elderly among those affected",
    "LIFE_EXPOSED": "{exposed} additional people detected in the affected area",
    "LIFE_PASSENGERS": "{passengers_onboard} passengers onboard",
    "HAZARD_FIRE": "Active fire",
    "HAZARD_SMOKE": "Smoke affecting the area",
    "HAZARD_COLLAPSED_STRUCTURE": "Structural collapse",
    "HAZARD_STRUCTURAL_DAMAGE": "Structural damage reported",
    "HAZARD_HAZARDOUS_MATERIAL": "Hazardous material involved",
    "HAZARD_TOXIC_GAS": "Toxic gas detected",
    "HAZARD_EXPLOSION_RISK": "Explosion risk",
    "HAZARD_DERAILMENT": "Rolling stock derailed",
    "HAZARD_POWER_LINES": "Power lines down",
    "HAZARD_WATER_DEPTH": "Flood water at {water_level_m} m",
    "HAZARD_GAS_STATION": "Fuel storage close to the incident",
    "HAZARD_COLLAPSE_ENTRAPMENT": "People trapped within collapsed structure",
    "HAZARD_DOWNWIND_EXPOSURE": "People exposed downwind of the release",
    "CONTEXT_ROAD_BLOCKED": "Access route blocked",
    "CONTEXT_HOSPITAL_DISTANCE": "Nearest hospital {hospital_distance_km} km away",
    "CONTEXT_WEATHER": "Weather condition: {weather}",
    "CONTEXT_WIND_SPEED": "Wind at {wind_speed_kmh} km/h",
    "CONTEXT_NIGHT": "Night-time operations",
}
