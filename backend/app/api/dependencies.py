"""Reusable FastAPI dependencies for request-scoped collaborators."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.llm.providers.groq_provider import GroqProvider
from app.database.session import get_db_session
from app.engines.allocation_engine import AllocationEngine
from app.engines.decision_engine import DecisionEngine
from app.exceptions import DetectorNotAvailableError
from app.repositories import IncidentRepository, ResourceRepository
from app.services.commander_brief import CommanderBriefGenerator
from app.services.commander_brief_llm import CommanderBriefLLMService
from app.services.incident_analysis import IncidentAnalysisService
from app.services.operations import (
    OperationsService,
    ResourceInventoryService,
    SystemStatusService,
)
from app.vision import BaseDetector, StaticDetector, UltralyticsYOLODetector, VisionService
from app.vision.config import YOLO_DETECTOR_CONFIG, YoloDetectorConfig

logger = logging.getLogger(__name__)

_STATIC_DETECTOR = "static"
_YOLO_DETECTOR = "yolo"
_GROQ_PROVIDER = "groq"


def _yolo_config() -> YoloDetectorConfig:
    settings = get_settings()
    model_path = settings.vision_model_path or YOLO_DETECTOR_CONFIG.model_path
    return YoloDetectorConfig(
        model_path=model_path,
        confidence_threshold=settings.vision_confidence_threshold,
        iou_threshold=settings.vision_iou_threshold,
        max_detections=settings.vision_max_detections,
        image_size=settings.vision_image_size,
        device=settings.vision_device,
    )


def build_detector() -> BaseDetector:
    """Construct the detector selected by configuration.

    The YOLO detector is loaded at startup so the first analysis request does not absorb the
    load cost. A broken or missing weights file does not prevent the application from starting
    — the detector records the failure and the system-status endpoint reports it.
    """
    settings = get_settings()
    backend = (settings.vision_detector or _STATIC_DETECTOR).strip().lower()

    if backend == _STATIC_DETECTOR:
        return StaticDetector(detections=[])
    if backend == _YOLO_DETECTOR:
        return UltralyticsYOLODetector(config=_yolo_config())
    raise DetectorNotAvailableError(f"Unknown vision detector backend: {backend}.")


@lru_cache
def get_vision_service() -> VisionService:
    """Return the process-wide vision service.

    Cached because detector construction may load a model, which should happen once rather
    than per request.
    """
    return VisionService(detector=build_detector())


@lru_cache
def get_decision_engine() -> DecisionEngine:
    """Return the process-wide decision engine, which is stateless and safe to share."""
    return DecisionEngine()


@lru_cache
def get_allocation_engine() -> AllocationEngine:
    """Return the process-wide allocation engine, which is stateless and safe to share."""
    return AllocationEngine()


@lru_cache
def get_brief_generator() -> CommanderBriefGenerator:
    """Return the process-wide commander-brief generator."""
    return CommanderBriefGenerator()


@lru_cache
def get_brief_narrator() -> CommanderBriefLLMService:
    """Return the process-wide commander-brief narrator.

    Construction never raises. A missing key, an unrecognised provider, or a bad configuration
    all yield a disabled narrator, and commander briefs stay deterministic.
    """
    settings = get_settings()
    provider_name = (settings.llm_provider or "").strip().lower()

    if provider_name != _GROQ_PROVIDER:
        return CommanderBriefLLMService(provider=None)

    api_key = (settings.groq_api_key or settings.llm_api_key or "").strip()
    if not api_key:
        logger.info(
            "LLM_PROVIDER is groq but no API key is configured; "
            "commander briefs remain deterministic."
        )
        return CommanderBriefLLMService(provider=None)

    try:
        provider = GroqProvider(
            api_key=api_key,
            model=(settings.llm_model or settings.groq_model),
            timeout_seconds=settings.llm_timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - narration is optional; never break startup
        logger.warning(
            "Groq provider could not be initialised (%s); commander briefs remain deterministic.",
            type(exc).__name__,
        )
        return CommanderBriefLLMService(provider=None)

    return CommanderBriefLLMService(
        provider=provider, timeout_seconds=settings.llm_timeout_seconds
    )


def get_operations_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> OperationsService:
    """Assemble the read-side operations feed service."""
    return OperationsService(incident_repository=IncidentRepository(session))


def get_resource_inventory_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ResourceInventoryService:
    """Assemble the resource inventory service."""
    return ResourceInventoryService(resource_repository=ResourceRepository(session))


def get_system_status_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> SystemStatusService:
    """Assemble the subsystem readiness service."""
    return SystemStatusService(session=session)


def get_incident_analysis_service(
    session: Annotated[Session, Depends(get_db_session)],
    vision_service: Annotated[VisionService, Depends(get_vision_service)],
    decision_engine: Annotated[DecisionEngine, Depends(get_decision_engine)],
    allocation_engine: Annotated[AllocationEngine, Depends(get_allocation_engine)],
    brief_generator: Annotated[CommanderBriefGenerator, Depends(get_brief_generator)],
    brief_narrator: Annotated[CommanderBriefLLMService, Depends(get_brief_narrator)],
) -> IncidentAnalysisService:
    """Assemble the request-scoped analysis workflow.

    Engines are shared because they hold no state; repositories are per-request because they
    are bound to the request's database session.
    """
    return IncidentAnalysisService(
        vision_service=vision_service,
        decision_engine=decision_engine,
        allocation_engine=allocation_engine,
        brief_generator=brief_generator,
        brief_narrator=brief_narrator,
        incident_repository=IncidentRepository(session),
        resource_repository=ResourceRepository(session),
    )
