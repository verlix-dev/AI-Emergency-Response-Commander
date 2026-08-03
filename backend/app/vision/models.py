"""Typed contracts for detector output and its normalized form."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DetectionClass(str, Enum):
    """Object classes the vision pipeline understands.

    Classes outside this set are discarded during parsing rather than guessed at, so an
    unfamiliar detector vocabulary can never silently influence an assessment.
    """

    PERSON = "person"
    FIRE = "fire"
    SMOKE = "smoke"
    CAR = "car"
    TRUCK = "truck"
    AMBULANCE = "ambulance"
    FIRE_TRUCK = "fire_truck"
    BOAT = "boat"
    BUILDING = "building"
    COLLAPSED_BUILDING = "collapsed_building"
    TRAIN = "train"
    DEBRIS = "debris"
    FLOOD_WATER = "flood_water"
    POWER_LINE = "power_line"
    TRAFFIC_INCIDENT = "traffic_incident"


class BoundingBox(BaseModel):
    """Axis-aligned box in absolute pixel coordinates, ordered ``x1 y1 x2 y2``."""

    model_config = ConfigDict(frozen=True)

    x1: float = Field(ge=0.0)
    y1: float = Field(ge=0.0)
    x2: float = Field(ge=0.0)
    y2: float = Field(ge=0.0)

    @property
    def width(self) -> float:
        """Return the box width in pixels."""
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        """Return the box height in pixels."""
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        """Return the box area in square pixels."""
        return self.width * self.height


class Detection(BaseModel):
    """One accepted detection, normalized to the supported class vocabulary."""

    model_config = ConfigDict(frozen=True)

    detection_class: DetectionClass
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox | None = None


class DiscardedDetection(BaseModel):
    """A detection the parser rejected, retained so the reason stays visible."""

    model_config = ConfigDict(frozen=True)

    raw_class: str
    confidence: float | None = None
    reason: str


class DetectionFrame(BaseModel):
    """Parsed detections for a single image, with frame geometry when known.

    ``width`` and ``height`` are optional because not every detector reports them. Rules that
    need frame geometry are skipped when it is absent instead of assuming a resolution.
    """

    model_config = ConfigDict(frozen=True)

    detections: tuple[Detection, ...] = ()
    discarded: tuple[DiscardedDetection, ...] = ()
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)

    @property
    def frame_area(self) -> float | None:
        """Return the frame area in square pixels, or ``None`` when geometry is unknown."""
        if self.width is None or self.height is None:
            return None
        return float(self.width * self.height)

    def of_class(self, detection_class: DetectionClass) -> tuple[Detection, ...]:
        """Return every accepted detection of one class, preserving parse order."""
        return tuple(item for item in self.detections if item.detection_class is detection_class)

    def count_of(self, detection_class: DetectionClass) -> int:
        """Return how many instances of a class were detected."""
        return len(self.of_class(detection_class))

    def contains(self, detection_class: DetectionClass) -> bool:
        """Return whether a class was detected at least once."""
        return any(item.detection_class is detection_class for item in self.detections)

    def max_confidence(self, detection_class: DetectionClass) -> float | None:
        """Return the strongest confidence for a class, or ``None`` when absent."""
        confidences = [item.confidence for item in self.of_class(detection_class)]
        return max(confidences) if confidences else None

    def coverage_fraction(self, detection_class: DetectionClass) -> float | None:
        """Return the fraction of the frame covered by a class's boxes.

        Overlapping boxes of the same class are summed and the result is clamped to 1.0, which
        is sufficient for the coarse banding this feeds and avoids a polygon-union dependency.
        Returns ``None`` when frame geometry or bounding boxes are unavailable.
        """
        frame_area = self.frame_area
        if frame_area is None or frame_area <= 0.0:
            return None
        boxes = [item.bbox for item in self.of_class(detection_class) if item.bbox is not None]
        if not boxes:
            return None
        return min(1.0, sum(box.area for box in boxes) / frame_area)
