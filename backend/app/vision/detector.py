"""Detector contracts and adapters that produce raw detections from an image.

Detectors return loosely-typed dictionaries rather than domain objects. Normalization is the
parser's job, which keeps every detector adapter thin and makes the vocabulary rules apply
uniformly no matter which detector produced the output.
"""

import threading
from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.exceptions import DetectorNotAvailableError, ImageNotReadableError
from app.vision.config import YOLO_DETECTOR_CONFIG, YoloDetectorConfig

# Loaded models keyed by resolved weights path. Ultralytics models are safe to reuse across
# calls, and loading is expensive, so each weights file is loaded at most once per process.
_MODEL_CACHE: dict[str, Any] = {}
_MODEL_CACHE_LOCK = threading.Lock()


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
    """Adapter over the trained Ultralytics YOLO model.

    The model is loaded when the detector is constructed, which happens once at startup, so the
    first analysis request does not absorb the load cost. Loading failure does not raise from the
    constructor: the error is retained and surfaced when detection is attempted, so a missing or
    corrupt weights file degrades the vision subsystem without preventing the application from
    starting or from reporting its own status.

    Ultralytics is imported inside the loader so that neither the application nor its tests
    require the dependency unless this detector is actually selected.
    """

    def __init__(
        self,
        config: YoloDetectorConfig = YOLO_DETECTOR_CONFIG,
        model_path: str | None = None,
        confidence_threshold: float | None = None,
        device: str | None = None,
    ) -> None:
        self._config = config
        self._model_path = model_path or config.model_path
        self._confidence_threshold = (
            confidence_threshold if confidence_threshold is not None else config.confidence_threshold
        )
        self._device = device if device is not None else config.device
        self._model: Any | None = None
        self._load_error: str | None = None
        self._load_model()

    @property
    def is_ready(self) -> bool:
        """Whether the model loaded successfully and inference can be attempted."""
        return self._model is not None

    @property
    def load_error(self) -> str | None:
        """Why the model failed to load, or ``None`` when it loaded successfully."""
        return self._load_error

    @property
    def model_path(self) -> str:
        """The weights file this detector was configured with."""
        return self._model_path

    def class_names(self) -> dict[int, str]:
        """Return the model's class-index to label mapping, empty when unloaded."""
        if self._model is None:
            return {}
        return dict(getattr(self._model, "names", {}) or {})

    def _load_model(self) -> Any | None:
        """Load the weights once per process, recording any failure rather than raising."""
        if self._model is not None:
            return self._model

        resolved = str(Path(self._model_path).resolve())
        cached = _MODEL_CACHE.get(resolved)
        if cached is not None:
            self._model = cached
            return cached

        with _MODEL_CACHE_LOCK:
            cached = _MODEL_CACHE.get(resolved)
            if cached is not None:
                self._model = cached
                return cached

            if not Path(resolved).is_file():
                self._load_error = f"Detector weights not found at {resolved}."
                return None

            try:
                from ultralytics import YOLO
            except ImportError:
                self._load_error = (
                    "The ultralytics package is not installed; YOLO detection is unavailable."
                )
                return None

            try:
                model = YOLO(resolved)
            except Exception as exc:  # noqa: BLE001 - any load failure must degrade, not crash
                self._load_error = f"Failed to load detector weights: {type(exc).__name__}: {exc}"
                return None

            _MODEL_CACHE[resolved] = model
            self._model = model
            self._load_error = None
            return model

    def _assert_decodable(self, image_path: str) -> None:
        """Reject an image the decoder cannot read.

        Ultralytics logs a warning and yields an empty result for an undecodable file rather
        than raising, which would surface to the operator as "no detections" — indistinguishable
        from a clean scene. Verifying up front turns a corrupt upload into an explicit error.
        """
        try:
            from PIL import Image
        except ImportError:
            return

        try:
            with Image.open(image_path) as image:
                image.verify()
        except Exception as exc:
            raise ImageNotReadableError(
                f"The image could not be decoded: {type(exc).__name__}."
            ) from exc

    def detect(self, image_path: str) -> Sequence[dict[str, Any]]:
        """Run inference and flatten the results into raw detection dictionaries.

        An image with no detections returns an empty sequence, which the pipeline treats as a
        valid result rather than an error.
        """
        if not Path(image_path).is_file():
            raise ImageNotReadableError(f"No readable image at {image_path}.")

        self._assert_decodable(image_path)

        model = self._load_model()
        if model is None:
            raise DetectorNotAvailableError(
                self._load_error or "The detection model is unavailable."
            )

        predict_options: dict[str, Any] = {
            "conf": self._confidence_threshold,
            "iou": self._config.iou_threshold,
            "max_det": self._config.max_detections,
            "imgsz": self._config.image_size,
            "verbose": False,
        }
        if self._device is not None:
            predict_options["device"] = self._device

        try:
            results = model.predict(image_path, **predict_options)
        except (OSError, ValueError) as exc:
            raise ImageNotReadableError(
                f"The image could not be decoded for inference: {type(exc).__name__}."
            ) from exc
        except Exception as exc:
            raise DetectorNotAvailableError(
                f"Inference failed: {type(exc).__name__}: {exc}"
            ) from exc

        return [detection for result in results for detection in self._flatten_result(result)]

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
