"""Reusable FastAPI dependencies for request-scoped collaborators."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db_session
from app.engines.allocation_engine import AllocationEngine
from app.engines.decision_engine import DecisionEngine
from app.exceptions import DetectorNotAvailableError
from app.repositories import IncidentRepository, ResourceRepository
from app.services.commander_brief import CommanderBriefGenerator
from app.services.incident_analysis import IncidentAnalysisService
from app.services.operations import (
    OperationsService,
    ResourceInventoryService,
    SystemStatusService,
)
from app.vision import BaseDetector, StaticDetector, UltralyticsYOLODetector, VisionService

_STATIC_DETECTOR = "static"
_YOLO_DETECTOR = "yolo"


def build_detector() -> BaseDetector:
    """Construct the detector selected by configuration.

    The static detector is the default so that the application starts without a model file
    present; it returns no detections, which the pipeline treats as a valid empty result.
    """
    settings = get_settings()
    backend = (settings.vision_detector or _STATIC_DETECTOR).strip().lower()

    if backend == _STATIC_DETECTOR:
        return StaticDetector(detections=[])
    if backend == _YOLO_DETECTOR:
        if not settings.vision_model_path:
            raise DetectorNotAvailableError(
                "VISION_MODEL_PATH must be set to use the YOLO detector."
            )
        return UltralyticsYOLODetector(
            model_path=settings.vision_model_path,
            confidence_threshold=settings.vision_confidence_threshold,
            device=settings.vision_device,
        )
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
        incident_repository=IncidentRepository(session),
        resource_repository=ResourceRepository(session),
    )
