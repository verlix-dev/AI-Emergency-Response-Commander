"""Orchestration of the vision pipeline.

The service composes a detector, a parser, and a mapper into the single public operation the
API needs. Each stage is injected so that the detector can be replaced, and so the parser and
mapper can be exercised without a model present.
"""

from app.engines.models import IncidentAssessment
from app.vision.detector import BaseDetector
from app.vision.mapper import AssessmentMapper
from app.vision.models import DetectionFrame
from app.vision.parser import DetectionParser


class VisionService:
    """Turn an image into an ``IncidentAssessment`` via detection, parsing, and mapping."""

    def __init__(
        self,
        detector: BaseDetector,
        parser: DetectionParser | None = None,
        mapper: AssessmentMapper | None = None,
    ) -> None:
        self._detector = detector
        self._parser = parser or DetectionParser()
        self._mapper = mapper or AssessmentMapper()

    def analyze(self, image_path: str) -> IncidentAssessment:
        """Return the assessment implied by the detections in one image."""
        return self._mapper.map(self.detect_frame(image_path))

    def detect_frame(self, image_path: str) -> DetectionFrame:
        """Return the parsed detection frame for an image.

        Exposed alongside ``analyze`` so callers that need the detections themselves, such as
        persistence or diagnostics, do not have to run the detector twice.
        """
        raw_detections = self._detector.detect(image_path)
        return self._parser.parse(raw_detections, frame=self._detector.frame_size(image_path))
