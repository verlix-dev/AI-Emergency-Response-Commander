"""Normalization of raw detector output into typed detections.

The parser is the only component that touches loosely-typed detector dictionaries. It accepts
what it recognises, discards the rest with a recorded reason, and never guesses: an unsupported
class or an unparseable confidence is dropped rather than coerced into something plausible.
"""

import re
from collections.abc import Sequence
from typing import Any

from app.vision.config import DETECTION_CLASS_ALIASES, MIN_DETECTION_CONFIDENCE
from app.vision.models import (
    BoundingBox,
    Detection,
    DetectionClass,
    DetectionFrame,
    DiscardedDetection,
)

_TOKEN_PATTERN = re.compile(r"[^a-z0-9]+")

_CLASS_KEYS: tuple[str, ...] = ("class", "class_name", "name", "label", "cls")
_CONFIDENCE_KEYS: tuple[str, ...] = ("confidence", "conf", "score", "probability")
_BBOX_KEYS: tuple[str, ...] = ("bbox", "box", "xyxy", "bounding_box")

_REASON_MISSING_CLASS = "class label missing"
_REASON_UNSUPPORTED_CLASS = "class not in supported vocabulary"
_REASON_MISSING_CONFIDENCE = "confidence missing or unparseable"
_REASON_CONFIDENCE_OUT_OF_RANGE = "confidence outside 0.0-1.0"
_REASON_BELOW_THRESHOLD = "confidence below minimum threshold"


def normalize_class_token(value: str) -> str:
    """Lower-case a class label and collapse punctuation and spacing into underscores."""
    return _TOKEN_PATTERN.sub("_", value.strip().lower()).strip("_")


class DetectionParser:
    """Convert raw detector dictionaries into a validated ``DetectionFrame``."""

    def __init__(self, min_confidence: float = MIN_DETECTION_CONFIDENCE) -> None:
        self._min_confidence = min_confidence

    def parse(
        self,
        raw_detections: Sequence[dict[str, Any]],
        frame: tuple[int, int] | None = None,
    ) -> DetectionFrame:
        """Parse every raw detection, partitioning them into accepted and discarded."""
        accepted: list[Detection] = []
        discarded: list[DiscardedDetection] = []

        for raw in raw_detections:
            detection, rejection = self._parse_one(raw)
            if detection is not None:
                accepted.append(detection)
            elif rejection is not None:
                discarded.append(rejection)

        width, height = frame if frame is not None else (None, None)
        return DetectionFrame(
            detections=tuple(accepted),
            discarded=tuple(discarded),
            width=width,
            height=height,
        )

    def _parse_one(
        self,
        raw: dict[str, Any],
    ) -> tuple[Detection | None, DiscardedDetection | None]:
        """Parse a single detection, returning either an acceptance or a rejection."""
        raw_class = self._extract_class(raw)
        confidence = self._extract_confidence(raw)

        if raw_class is None:
            return None, DiscardedDetection(
                raw_class="", confidence=confidence, reason=_REASON_MISSING_CLASS
            )

        detection_class = self._resolve_class(raw_class)
        if detection_class is None:
            return None, DiscardedDetection(
                raw_class=raw_class, confidence=confidence, reason=_REASON_UNSUPPORTED_CLASS
            )

        if confidence is None:
            return None, DiscardedDetection(
                raw_class=raw_class, confidence=None, reason=_REASON_MISSING_CONFIDENCE
            )
        if not 0.0 <= confidence <= 1.0:
            return None, DiscardedDetection(
                raw_class=raw_class,
                confidence=confidence,
                reason=_REASON_CONFIDENCE_OUT_OF_RANGE,
            )
        if confidence < self._min_confidence:
            return None, DiscardedDetection(
                raw_class=raw_class, confidence=confidence, reason=_REASON_BELOW_THRESHOLD
            )

        return (
            Detection(
                detection_class=detection_class,
                confidence=confidence,
                bbox=self._extract_bbox(raw),
            ),
            None,
        )

    def _extract_class(self, raw: dict[str, Any]) -> str | None:
        """Return the first recognised class-label key, as a non-empty string."""
        for key in _CLASS_KEYS:
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _resolve_class(self, raw_class: str) -> DetectionClass | None:
        """Map a raw label onto the supported vocabulary, or ``None`` when unsupported."""
        token = normalize_class_token(raw_class)
        if not token:
            return None
        alias = DETECTION_CLASS_ALIASES.get(token)
        if alias is not None:
            return alias
        try:
            return DetectionClass(token)
        except ValueError:
            return None

    def _extract_confidence(self, raw: dict[str, Any]) -> float | None:
        """Return the first recognised confidence key coerced to a float."""
        for key in _CONFIDENCE_KEYS:
            if key not in raw:
                continue
            try:
                return float(raw[key])
            except (TypeError, ValueError):
                return None
        return None

    def _extract_bbox(self, raw: dict[str, Any]) -> BoundingBox | None:
        """Return a bounding box when four usable coordinates are present.

        A malformed or partial box is dropped while the detection itself is kept: the class and
        confidence remain trustworthy, and only the area-based rules lose their input.
        """
        for key in _BBOX_KEYS:
            if key not in raw:
                continue
            coordinates = self._coerce_coordinates(raw[key])
            if coordinates is None:
                continue
            x1, y1, x2, y2 = coordinates
            return BoundingBox(
                x1=min(x1, x2), y1=min(y1, y2), x2=max(x1, x2), y2=max(y1, y2)
            )
        return None

    def _coerce_coordinates(self, value: Any) -> tuple[float, float, float, float] | None:
        """Flatten and validate a bounding-box value into four non-negative floats."""
        if isinstance(value, dict):
            if not all(axis in value for axis in ("x1", "y1", "x2", "y2")):
                return None
            value = [value["x1"], value["y1"], value["x2"], value["y2"]]

        tolist = getattr(value, "tolist", None)
        if callable(tolist):
            value = tolist()
        while (
            isinstance(value, (list, tuple))
            and len(value) == 1
            and isinstance(value[0], (list, tuple))
        ):
            value = value[0]
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            return None

        try:
            coordinates = tuple(float(item) for item in value)
        except (TypeError, ValueError):
            return None
        if any(coordinate < 0.0 for coordinate in coordinates):
            return None
        return coordinates  # type: ignore[return-value]
