"""Deterministic mapping from parsed detections onto an ``IncidentAssessment``.

The mapper only asserts what the detections support. A field is populated when a detection
gives direct evidence for it, and left as ``None`` otherwise, because the decision engine treats
``None`` as "not reported" and a concrete value as a reported fact. Filling gaps with defaults
here would manufacture evidence and inflate the engine's confidence.
"""

from app.engines.models import IncidentAssessment
from app.vision.config import (
    INCIDENT_TYPE_RULES,
    RESPONDER_VEHICLE_CLASSES,
    ROAD_BLOCKED_DEBRIS_COUNT,
    UNCLASSIFIED_INCIDENT_TYPE,
    VEHICLE_CLASSES,
    VISION_MAPPING_CONFIG,
    WATER_DEPTH_COVERAGE_BANDS,
    WATER_DEPTH_WITHOUT_GEOMETRY_M,
    VisionMappingConfig,
)
from app.vision.models import DetectionClass, DetectionFrame


class AssessmentMapper:
    """Translate a ``DetectionFrame`` into an ``IncidentAssessment``."""

    def __init__(self, config: VisionMappingConfig = VISION_MAPPING_CONFIG) -> None:
        self._config = config

    def map(self, frame: DetectionFrame) -> IncidentAssessment:
        """Build an assessment from the detections in one frame."""
        return IncidentAssessment(
            incident_type=self._incident_type(frame),
            people_detected=self._people_detected(frame),
            fire_detected=self._hazard_flag(frame, DetectionClass.FIRE),
            smoke_detected=self._hazard_flag(frame, DetectionClass.SMOKE),
            collapsed_structure=self._collapsed_structure(frame),
            structural_damage=self._structural_damage(frame),
            power_lines_down=self._hazard_flag(frame, DetectionClass.POWER_LINE),
            water_level_m=self._water_level(frame),
            road_blocked=self._road_blocked(frame),
            responders_on_scene=self._responders_on_scene(frame),
        )

    def _incident_type(self, frame: DetectionFrame) -> str:
        """Classify the incident from the detected classes.

        The first matching rule wins, and rules are ordered so that the most specific evidence
        is tested first. With no matching evidence the type is left unclassified rather than
        guessed, which the decision engine handles by applying its conservative generic profile.
        """
        if not frame.detections:
            return UNCLASSIFIED_INCIDENT_TYPE
        for incident_type, required_classes in INCIDENT_TYPE_RULES:
            if all(frame.contains(item) for item in required_classes):
                return incident_type
        if frame.contains(DetectionClass.FIRE):
            return "Building Fire"
        if frame.contains(DetectionClass.TRAIN):
            return "Train Accident"
        if self._detected_vehicle_count(frame) > 0 and frame.contains(DetectionClass.DEBRIS):
            return "Road Accident"
        return UNCLASSIFIED_INCIDENT_TYPE

    def _people_detected(self, frame: DetectionFrame) -> int | None:
        """Return the person count, or ``None`` when nothing at all was detected.

        A count of zero is only reported when the detector did find something: an empty frame
        cannot distinguish "nobody present" from "nothing detected", and reporting zero people
        for an empty frame would assert an absence the detector never established.
        """
        if not frame.detections:
            return None
        return frame.count_of(DetectionClass.PERSON)

    def _hazard_flag(self, frame: DetectionFrame, detection_class: DetectionClass) -> bool | None:
        """Return ``True`` when a hazard is detected confidently, else ``None``.

        Absence is never reported as ``False``. A detector that does not see smoke has not
        established that there is no smoke, so the field stays unreported.
        """
        confidence = frame.max_confidence(detection_class)
        if confidence is None:
            return None
        if confidence >= self._config.hazard_assertion_confidence:
            return True
        return None

    def _collapsed_structure(self, frame: DetectionFrame) -> bool | None:
        """Assert collapse only on strong evidence, given it drives a severity floor."""
        confidence = frame.max_confidence(DetectionClass.COLLAPSED_BUILDING)
        if confidence is None:
            return None
        if confidence >= self._config.collapse_assertion_confidence:
            return True
        return None

    def _structural_damage(self, frame: DetectionFrame) -> bool | None:
        """Infer structural damage from a confirmed collapse or from detected debris."""
        if self._collapsed_structure(frame):
            return True
        confidence = frame.max_confidence(DetectionClass.DEBRIS)
        if confidence is not None and confidence >= self._config.hazard_assertion_confidence:
            return True
        return None

    def _water_level(self, frame: DetectionFrame) -> float | None:
        """Estimate a water depth category from the frame area covered by flood water.

        This is a coarse category, not a measurement: a single camera cannot determine depth,
        and the coverage fraction only indicates how much of the view is inundated. When frame
        geometry is unavailable a conservative shallow default is used, so that the presence of
        water is still reported without implying a depth the image cannot support.
        """
        confidence = frame.max_confidence(DetectionClass.FLOOD_WATER)
        if confidence is None or confidence < self._config.water_assertion_confidence:
            return None

        coverage = frame.coverage_fraction(DetectionClass.FLOOD_WATER)
        if coverage is None:
            return WATER_DEPTH_WITHOUT_GEOMETRY_M
        for threshold, depth in WATER_DEPTH_COVERAGE_BANDS:
            if coverage >= threshold:
                return depth
        return WATER_DEPTH_WITHOUT_GEOMETRY_M

    def _road_blocked(self, frame: DetectionFrame) -> bool | None:
        """Assert a blocked road from a collapse or from multiple debris detections."""
        if self._collapsed_structure(frame):
            return True
        debris = [
            item
            for item in frame.of_class(DetectionClass.DEBRIS)
            if item.confidence >= self._config.road_blocked_confidence
        ]
        if len(debris) >= ROAD_BLOCKED_DEBRIS_COUNT:
            return True
        return None

    def _responders_on_scene(self, frame: DetectionFrame) -> int | None:
        """Count emergency vehicles present, which indicates a response already underway."""
        responders = [
            item
            for item in frame.detections
            if item.detection_class in RESPONDER_VEHICLE_CLASSES
            and item.confidence >= self._config.responder_assertion_confidence
        ]
        if not responders:
            return None
        return len(responders)

    def _detected_vehicle_count(self, frame: DetectionFrame) -> int:
        """Return the total number of detected vehicles of any class."""
        return sum(frame.count_of(item) for item in VEHICLE_CLASSES)
