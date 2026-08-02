"""Detector contracts and adapters that produce raw detections from an image.

Detectors return loosely-typed dictionaries rather than domain objects. Normalization is the
parser's job, which keeps every detector adapter thin and makes the vocabulary rules apply
uniformly no matter which detector produced the output.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.exceptions import DetectorNotAvailableError, ImageNotReadableError


class BaseDetector(ABC):
    """Contract every detector adapter must satisfy."""

    @abstractmethod
    def detect(self, image_path: str) -> Sequence[dict[str, Any]]:
        """Return raw detections for an image.

        Each item should carry a class label, a confidence, and optionally a bounding box.
        Implementations must not raise for an empty result: no detections is a valid outcome.
        """

    def frame_size(self, image_path: str) -> tuple[int, int] | None:
        """Return ``(width, height)`` in pixels when the detector can report it.

        Frame geometry is optional. Returning ``None`` disables the area-based rules rather
        than causing the pipeline to assume a resolution.
        """
        return None


class StaticDetector(BaseDetector):
    """Detector returning a fixed detection list, independent of the image.

    Used for tests and for callers that already hold detections from an out-of-process
    detector, so the rest of the pipeline can be exercised without a model dependency.
    """

    def __init__(
        self,
        detections: Sequence[dict[str, Any]],
        frame: tuple[int, int] | None = None,
    ) -> None:
        self._detections = list(detections)
        self._frame = frame

    def detect(self, image_path: str) -> Sequence[dict[str, Any]]:
        """Return the configured detections verbatim."""
        return list(self._detections)

    def frame_size(self, image_path: str) -> tuple[int, int] | None:
        """Return the configured frame size, if one was supplied."""
        return self._frame


class UltralyticsYOLODetector(BaseDetector):
    """Adapter over an Ultralytics YOLO model.

    The Ultralytics package is imported lazily so that neither the application nor its tests
    require the dependency until a caller actually selects this detector. Model loading is
    deferred to the first detection and then cached.
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.25,
        device: str | None = None,
    ) -> None:
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold
        self._device = device
        self._model: Any | None = None

    def _load_model(self) -> Any:
        """Load and cache the underlying model, translating import failure into a domain error."""
        if self._model is not None:
            return self._model
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise DetectorNotAvailableError(
                "The ultralytics package is not installed; YOLO detection is unavailable."
            ) from exc
        self._model = YOLO(self._model_path)
        return self._model

    def detect(self, image_path: str) -> Sequence[dict[str, Any]]:
        """Run the model and flatten its results into raw detection dictionaries."""
        if not Path(image_path).is_file():
            raise ImageNotReadableError(f"No readable image at {image_path}.")

        model = self._load_model()
        predict_options: dict[str, Any] = {"conf": self._confidence_threshold, "verbose": False}
        if self._device is not None:
            predict_options["device"] = self._device

        results = model.predict(image_path, **predict_options)
        return [
            detection
            for result in results
            for detection in self._flatten_result(result)
        ]

    def _flatten_result(self, result: Any) -> list[dict[str, Any]]:
        """Convert one Ultralytics result object into raw detection dictionaries.

        Ultralytics exposes boxes as tensors and class names as an index-to-label mapping, so
        each box is resolved back to its label here. Boxes whose class index is missing from
        the mapping are emitted with their raw index, letting the parser discard them under the
        usual unsupported-class rule.
        """
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return []

        names: dict[int, str] = dict(getattr(result, "names", {}) or {})
        detections: list[dict[str, Any]] = []

        for box in boxes:
            class_index = int(self._scalar(box.cls))
            detections.append(
                {
                    "class": names.get(class_index, str(class_index)),
                    "confidence": float(self._scalar(box.conf)),
                    "bbox": [float(value) for value in self._sequence(box.xyxy)],
                }
            )
        return detections

    def _scalar(self, value: Any) -> float:
        """Reduce a tensor or sequence holding one number to a plain float."""
        item = getattr(value, "item", None)
        if callable(item):
            try:
                return float(item())
            except (TypeError, ValueError, RuntimeError):
                pass
        if isinstance(value, (list, tuple)):
            return float(value[0])
        return float(value)

    def _sequence(self, value: Any) -> Sequence[float]:
        """Flatten a tensor or nested sequence of coordinates into a flat sequence."""
        tolist = getattr(value, "tolist", None)
        if callable(tolist):
            value = tolist()
        while isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], (list, tuple)):
            value = value[0]
        return list(value)

    def frame_size(self, image_path: str) -> tuple[int, int] | None:
        """Return the image dimensions when Pillow is available to read them."""
        try:
            from PIL import Image
        except ImportError:
            return None
        try:
            with Image.open(image_path) as image:
                return int(image.width), int(image.height)
        except (OSError, ValueError):
            return None
