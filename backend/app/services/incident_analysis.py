"""End-to-end incident analysis orchestration.

This service is the primary ARES backend workflow. It sequences the existing engines and
persists the outcome, but contains no reasoning of its own: vision decides what is visible, the
decision engine decides what it means, the allocation engine decides what to send, and the brief
generator decides how to say it. The orchestrator only wires them together and records the
result.
"""

from datetime import datetime, timezone
from uuid import UUID

from app.engines.allocation_engine import AllocationEngine, AvailableResource, resolve_resource_kind
from app.engines.allocation_models import AllocationResult
from app.engines.decision_engine import DecisionEngine
from app.engines.models import DecisionResult, IncidentAssessment
from app.exceptions import NotFoundError
from app.models.action_plan import ActionPlan
from app.models.enums import IncidentStatus
from app.models.incident import Incident
from app.models.incident_analysis import IncidentAnalysis
from app.models.vision_result import VisionResult
from app.repositories import IncidentRepository, ResourceRepository
from app.schemas.analysis import (
    CommanderBrief,
    DetectionBoxSchema,
    IncidentAnalysisResponse,
    IncidentTimelineResponse,
    SceneSchema,
)
from app.services.commander_brief import CommanderBriefGenerator
from app.services.commander_brief_llm import CommanderBriefLLMService
from app.vision import AssessmentMapper, DetectionClass, DetectionFrame, VisionService
from app.vision.config import VEHICLE_CLASSES

DEFAULT_LOCATION = "Unknown"
MAX_TITLE_LENGTH = 200
MAX_LOCATION_LENGTH = 300


class IncidentAnalysisService:
    """Run an image through every stage and persist the resulting command picture."""

    def __init__(
        self,
        vision_service: VisionService,
        decision_engine: DecisionEngine,
        allocation_engine: AllocationEngine,
        brief_generator: CommanderBriefGenerator,
        incident_repository: IncidentRepository,
        resource_repository: ResourceRepository,
        mapper: AssessmentMapper | None = None,
        brief_narrator: CommanderBriefLLMService | None = None,
    ) -> None:
        self._vision_service = vision_service
        self._decision_engine = decision_engine
        self._allocation_engine = allocation_engine
        self._brief_generator = brief_generator
        self._incidents = incident_repository
        self._resources = resource_repository
        self._mapper = mapper or AssessmentMapper()
        self._brief_narrator = brief_narrator

    def _compose_brief(
        self,
        assessment: IncidentAssessment,
        decision: DecisionResult,
        allocation: AllocationResult,
    ) -> CommanderBrief:
        """Generate the deterministic brief, then narrate it when narration is available.

        The deterministic brief is always produced first and is what gets returned if narration
        is unconfigured, fails, or produces ungrounded text.
        """
        brief = self._brief_generator.generate(assessment, decision, allocation)
        if self._brief_narrator is None or not self._brief_narrator.is_enabled:
            return brief
        return self._brief_narrator.narrate(brief, assessment, decision, allocation).brief

    def analyze_image(
        self,
        image_path: str,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        title: str | None = None,
    ) -> IncidentAnalysisResponse:
        """Analyse one image end to end and persist a new incident with its first revision."""
        frame = self._vision_service.detect_frame(image_path)
        assessment = self._mapper.map(frame)
        decision = self._decision_engine.decide(assessment)
        allocation = self._allocate(assessment, decision)
        brief = self._compose_brief(assessment, decision, allocation)

        incident = self._incidents.add_incident(
            Incident(
                title=self._title(title, decision),
                description=decision.explanation.current_situation,
                incident_type=decision.disaster_type.value,
                status=IncidentStatus.PLANNED,
                priority=decision.priority_level.value,
                location=(location or DEFAULT_LOCATION)[:MAX_LOCATION_LENGTH],
                latitude=latitude,
                longitude=longitude,
            )
        )

        self._persist_vision_result(incident.id, frame)
        self._persist_action_plan(incident.id, brief)
        self._persist_analysis(incident.id, assessment, decision, allocation, brief)

        return IncidentAnalysisResponse(
            incident=incident,
            assessment=assessment,
            decision=decision,
            resources=allocation,
            commander_brief=brief,
            scene=self._build_scene(frame),
            timestamp=datetime.now(timezone.utc),
        )

    def reanalyze_incident(self, incident_id: UUID, image_path: str) -> IncidentAnalysisResponse:
        """Analyse a further image against an existing incident, appending a new revision."""
        incident = self._require_incident(incident_id)

        frame = self._vision_service.detect_frame(image_path)
        assessment = self._mapper.map(frame)
        decision = self._decision_engine.decide(assessment)
        allocation = self._allocate(assessment, decision)
        brief = self._compose_brief(assessment, decision, allocation)

        incident.incident_type = decision.disaster_type.value
        incident.priority = decision.priority_level.value
        incident.description = decision.explanation.current_situation

        self._persist_vision_result(incident.id, frame)
        self._persist_action_plan(incident.id, brief)
        self._persist_analysis(incident.id, assessment, decision, allocation, brief)

        return IncidentAnalysisResponse(
            incident=incident,
            assessment=assessment,
            decision=decision,
            resources=allocation,
            commander_brief=brief,
            scene=self._build_scene(frame),
            timestamp=datetime.now(timezone.utc),
        )

    def get_timeline(self, incident_id: UUID) -> IncidentTimelineResponse:
        """Return an incident with every analysis revision recorded against it."""
        incident = self._require_incident(incident_id)
        return IncidentTimelineResponse(
            incident=incident,
            revisions=self._incidents.list_analyses(incident_id),
        )

    def _require_incident(self, incident_id: UUID) -> Incident:
        """Return an incident or raise the domain not-found error."""
        incident = self._incidents.get_incident(incident_id)
        if incident is None:
            raise NotFoundError(f"No incident with id {incident_id}.")
        return incident

    def _build_scene(self, frame: DetectionFrame) -> SceneSchema:
        """Expose the detections behind an analysis so the client can overlay them."""
        return SceneSchema(
            detections=[
                DetectionBoxSchema(
                    detection_class=detection.detection_class.value,
                    confidence=detection.confidence,
                    x1=detection.bbox.x1 if detection.bbox else None,
                    y1=detection.bbox.y1 if detection.bbox else None,
                    x2=detection.bbox.x2 if detection.bbox else None,
                    y2=detection.bbox.y2 if detection.bbox else None,
                )
                for detection in frame.detections
            ],
            discarded_count=len(frame.discarded),
            frame_width=frame.width,
            frame_height=frame.height,
        )

    def _allocate(
        self,
        assessment: IncidentAssessment,
        decision: DecisionResult,
    ) -> AllocationResult:
        """Match the decision's requirements against the currently available resource pool."""
        available: list[AvailableResource] = []
        for resource in self._resources.list_available():
            kind = resolve_resource_kind(resource.resource_type)
            if kind is not None:
                available.append(AvailableResource(kind, resource.resource_name))
        return self._allocation_engine.allocate(assessment, decision, available)

    def _title(self, provided: str | None, decision: DecisionResult) -> str:
        """Use the caller's title, or derive one from the classification and severity."""
        if provided and provided.strip():
            return provided.strip()[:MAX_TITLE_LENGTH]
        readable = decision.disaster_type.value.replace("_", " ").title()
        return f"{readable} - {decision.severity_level.value}"[:MAX_TITLE_LENGTH]

    def _persist_vision_result(self, incident_id: UUID, frame: DetectionFrame) -> None:
        """Record the detection counts behind this analysis.

        Populates the existing vision-results table so the detections that drove the decision
        remain inspectable alongside it.
        """
        confidences = [detection.confidence for detection in frame.detections]
        vision_result = VisionResult(
            incident_id=incident_id,
            people_detected=frame.count_of(DetectionClass.PERSON),
            vehicles_detected=sum(frame.count_of(item) for item in VEHICLE_CLASSES),
            boats_detected=frame.count_of(DetectionClass.BOAT),
            collapsed_structures=frame.count_of(DetectionClass.COLLAPSED_BUILDING),
            confidence_score=round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        )
        self._incidents.add_vision_result(vision_result)

    def _persist_action_plan(self, incident_id: UUID, brief: CommanderBrief) -> None:
        """Store the rendered brief as the incident's action plan."""
        self._incidents.add_action_plan(
            ActionPlan(incident_id=incident_id, generated_plan=brief.as_text())
        )

    def _persist_analysis(
        self,
        incident_id: UUID,
        assessment: IncidentAssessment,
        decision: DecisionResult,
        allocation: AllocationResult,
        brief: CommanderBrief,
    ) -> None:
        """Append the full analysis snapshot as a new revision."""
        self._incidents.add_analysis(
            IncidentAnalysis(
                incident_id=incident_id,
                revision=self._incidents.next_revision(incident_id),
                severity_level=decision.severity_level.value,
                severity_score=decision.severity_score,
                priority_level=decision.priority_level.value,
                priority_score=decision.priority_score,
                confidence=decision.confidence,
                assessment=assessment.model_dump(mode="json"),
                decision=decision.model_dump(mode="json"),
                resources=allocation.model_dump(mode="json"),
                commander_brief=brief.model_dump(mode="json"),
            )
        )
