"""Thresholds, class aliases, and mapping tables for the vision pipeline.

Every tunable value used when turning detections into an assessment is defined here, so the
parser and mapper hold logic while this module holds numbers.
"""

from dataclasses import dataclass

from app.vision.models import DetectionClass

MIN_DETECTION_CONFIDENCE = 0.25

DETECTION_CLASS_ALIASES: dict[str, DetectionClass] = {
    "person": DetectionClass.PERSON,
    "people": DetectionClass.PERSON,
    "pedestrian": DetectionClass.PERSON,
    "human": DetectionClass.PERSON,
    "fire": DetectionClass.FIRE,
    "flame": DetectionClass.FIRE,
    "flames": DetectionClass.FIRE,
    "smoke": DetectionClass.SMOKE,
    "car": DetectionClass.CAR,
    "vehicle": DetectionClass.CAR,
    "truck": DetectionClass.TRUCK,
    "lorry": DetectionClass.TRUCK,
    "bus": DetectionClass.TRUCK,
    "ambulance": DetectionClass.AMBULANCE,
    "fire_truck": DetectionClass.FIRE_TRUCK,
    "firetruck": DetectionClass.FIRE_TRUCK,
    "fire_engine": DetectionClass.FIRE_TRUCK,
    "boat": DetectionClass.BOAT,
    "ship": DetectionClass.BOAT,
    "building": DetectionClass.BUILDING,
    "house": DetectionClass.BUILDING,
    "structure": DetectionClass.BUILDING,
    "collapsed_building": DetectionClass.COLLAPSED_BUILDING,
    "building_collapse": DetectionClass.COLLAPSED_BUILDING,
    "collapsed_structure": DetectionClass.COLLAPSED_BUILDING,
    "rubble": DetectionClass.COLLAPSED_BUILDING,
    "train": DetectionClass.TRAIN,
    "locomotive": DetectionClass.TRAIN,
    "railcar": DetectionClass.TRAIN,
    "debris": DetectionClass.DEBRIS,
    "wreckage": DetectionClass.DEBRIS,
    "flood_water": DetectionClass.FLOOD_WATER,
    "floodwater": DetectionClass.FLOOD_WATER,
    "water": DetectionClass.FLOOD_WATER,
    "flood": DetectionClass.FLOOD_WATER,
    "power_line": DetectionClass.POWER_LINE,
    "powerline": DetectionClass.POWER_LINE,
    "power_lines": DetectionClass.POWER_LINE,
    "electric_line": DetectionClass.POWER_LINE,
}

VEHICLE_CLASSES: tuple[DetectionClass, ...] = (
    DetectionClass.CAR,
    DetectionClass.TRUCK,
    DetectionClass.AMBULANCE,
    DetectionClass.FIRE_TRUCK,
)

RESPONDER_VEHICLE_CLASSES: tuple[DetectionClass, ...] = (
    DetectionClass.AMBULANCE,
    DetectionClass.FIRE_TRUCK,
)

WATER_DEPTH_COVERAGE_BANDS: tuple[tuple[float, float], ...] = (
    (0.50, 1.5),
    (0.25, 0.8),
    (0.10, 0.4),
    (0.00, 0.2),
)

WATER_DEPTH_WITHOUT_GEOMETRY_M = 0.4

ROAD_BLOCKED_DEBRIS_COUNT = 2


@dataclass(frozen=True)
class VisionMappingConfig:
    """Confidence gates for asserting a condition from detections.

    Gates differ by consequence. Asserting a hazard is *present* needs only moderate evidence
    because under-reporting a hazard is the costlier error. Asserting a structure has
    *collapsed* is gated higher, since it drives severity floors in the decision engine.
    """

    min_confidence: float = MIN_DETECTION_CONFIDENCE
    hazard_assertion_confidence: float = 0.40
    collapse_assertion_confidence: float = 0.60
    water_assertion_confidence: float = 0.45
    responder_assertion_confidence: float = 0.50
    road_blocked_confidence: float = 0.50


VISION_MAPPING_CONFIG = VisionMappingConfig()

UNCLASSIFIED_INCIDENT_TYPE = "Unknown"

INCIDENT_TYPE_RULES: tuple[tuple[str, tuple[DetectionClass, ...]], ...] = (
    ("Building Collapse", (DetectionClass.COLLAPSED_BUILDING,)),
    ("Flood", (DetectionClass.FLOOD_WATER,)),
    ("Building Fire", (DetectionClass.FIRE, DetectionClass.BUILDING)),
    ("Train Accident", (DetectionClass.TRAIN, DetectionClass.DEBRIS)),
)
