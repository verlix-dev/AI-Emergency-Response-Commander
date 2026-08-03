"""Read-side services backing the operations feed, inventory, and status board.

These services only project data the pipeline already produces. They add no reasoning: counts
come from the resource table, gradings come from persisted analyses, and readiness comes from
the components the application actually depends on.
"""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.engines.allocation_engine import resolve_resource_kind
from app.engines.allocation_models import ResourceKind
from app.repositories import IncidentRepository, ResourceRepository
from app.schemas.analysis import (
    ComponentHealthSchema,
    IncidentListResponse,
    IncidentSummarySchema,
    ResourceInventoryItemSchema,
    ResourceInventoryResponse,
    SystemStatusResponse,
)

STATUS_OPERATIONAL = "OPERATIONAL"
STATUS_DEGRADED = "DEGRADED"
STATUS_OFFLINE = "OFFLINE"

RESOURCE_KIND_LABELS: dict[ResourceKind, str] = {
    ResourceKind.FIRE_TRUCK: "Fire Trucks",
    ResourceKind.AMBULANCE: "Ambulances",
    ResourceKind.POLICE: "Police Units",
    ResourceKind.SEARCH_RESCUE: "Search & Rescue",
    ResourceKind.BOAT: "Boats",
    ResourceKind.MEDICAL_TEAM: "Medical Teams",
    ResourceKind.HAZMAT: "Hazmat Units",
    ResourceKind.HEAVY_MACHINERY: "Heavy Equipment",
}


class OperationsService:
    """Project persisted incidents into the operations feed."""

    def __init__(self, incident_repository: IncidentRepository) -> None:
        self._incidents = incident_repository

    def list_incidents(self, limit: int = 50, offset: int = 0) -> IncidentListResponse:
        """Return incidents newest first, each carrying its most recent grading."""
        incidents = self._incidents.list_incidents(limit=limit, offset=offset)
        summaries: list[IncidentSummarySchema] = []

        for incident in incidents:
            revisions = incident.analyses
            latest = max(revisions, key=lambda item: item.revision) if revisions else None
            summaries.append(
                IncidentSummarySchema(
                    id=incident.id,
                    title=incident.title,
                    incident_type=incident.incident_type,
                    status=incident.status.value,
                    priority=incident.priority,
                    location=incident.location,
                    latitude=incident.latitude,
                    longitude=incident.longitude,
                    severity_level=latest.severity_level if latest else None,
                    severity_score=latest.severity_score if latest else None,
                    priority_score=latest.priority_score if latest else None,
                    confidence=latest.confidence if latest else None,
                    revision_count=len(revisions),
                    created_at=incident.created_at,
                    updated_at=incident.updated_at,
                )
            )

        return IncidentListResponse(
            incidents=summaries, total=self._incidents.count_incidents()
        )


class ResourceInventoryService:
    """Group the resource table into the kinds the allocation engine understands."""

    def __init__(self, resource_repository: ResourceRepository) -> None:
        self._resources = resource_repository

    def get_inventory(self) -> ResourceInventoryResponse:
        """Return standing stock per resource kind, including unavailable units."""
        grouped: dict[ResourceKind, dict[str, object]] = {}
        unrecognised: list[str] = []

        for resource in self._resources.list_all():
            kind = resolve_resource_kind(resource.resource_type)
            if kind is None:
                if resource.resource_type not in unrecognised:
                    unrecognised.append(resource.resource_type)
                continue
            bucket = grouped.setdefault(
                kind, {"total": 0, "available": 0, "names": []}
            )
            bucket["total"] = int(bucket["total"]) + 1
            if resource.available:
                bucket["available"] = int(bucket["available"]) + 1
                names = bucket["names"]
                assert isinstance(names, list)
                names.append(resource.resource_name)

        items = [
            ResourceInventoryItemSchema(
                resource_kind=kind.value,
                label=RESOURCE_KIND_LABELS[kind],
                total=int(grouped[kind]["total"]),
                available=int(grouped[kind]["available"]),
                unavailable=int(grouped[kind]["total"]) - int(grouped[kind]["available"]),
                resource_names=list(grouped[kind]["names"]),  # type: ignore[arg-type]
            )
            for kind in RESOURCE_KIND_LABELS
            if kind in grouped
        ]

        return ResourceInventoryResponse(
            items=items,
            total_units=sum(item.total for item in items),
            available_units=sum(item.available for item in items),
            unrecognised_types=unrecognised,
        )


class SystemStatusService:
    """Report readiness of the subsystems the application genuinely depends on."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_status(self) -> SystemStatusResponse:
        """Probe each subsystem and summarise overall readiness."""
        settings = get_settings()
        components = [
            self._database_component(),
            self._vision_component(),
            self._decision_component(),
            self._resource_component(),
            self._api_component(),
        ]
        overall = STATUS_OPERATIONAL
        if any(item.status == STATUS_OFFLINE for item in components):
            overall = STATUS_OFFLINE
        elif any(item.status == STATUS_DEGRADED for item in components):
            overall = STATUS_DEGRADED

        return SystemStatusResponse(
            status=overall,
            version=settings.app_version,
            environment=settings.environment,
            components=components,
            checked_at=datetime.now(timezone.utc),
        )

    def _database_component(self) -> ComponentHealthSchema:
        """Verify the database answers a trivial query."""
        try:
            self._session.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            return ComponentHealthSchema(
                component="database",
                label="Database",
                status=STATUS_OFFLINE,
                detail=f"Connection failed: {type(exc).__name__}",
            )
        return ComponentHealthSchema(
            component="database",
            label="Database",
            status=STATUS_OPERATIONAL,
            detail="Connection healthy.",
        )

    def _vision_component(self) -> ComponentHealthSchema:
        """Report whether the configured detector actually loaded and can serve.

        Readiness is taken from the constructed detector rather than inferred from settings,
        because the model path now defaults to the bundled weights: a detector can be fully
        operational without an explicit path being configured.
        """
        settings = get_settings()
        backend = (settings.vision_detector or "static").strip().lower()

        if backend == "static":
            return ComponentHealthSchema(
                component="vision",
                label="Vision Engine",
                status=STATUS_DEGRADED,
                detail="Static detector active; no model loaded.",
            )

        try:
            from app.api.dependencies import get_vision_service

            detector = get_vision_service().detector
        except Exception as exc:  # noqa: BLE001 - status must report, never propagate
            return ComponentHealthSchema(
                component="vision",
                label="Vision Engine",
                status=STATUS_OFFLINE,
                detail=f"Detector unavailable: {type(exc).__name__}.",
            )

        is_ready = getattr(detector, "is_ready", True)
        if not is_ready:
            return ComponentHealthSchema(
                component="vision",
                label="Vision Engine",
                status=STATUS_OFFLINE,
                detail=getattr(detector, "load_error", None) or "Detector model failed to load.",
            )

        class_count = len(getattr(detector, "class_names", dict)() or {})
        detail = f"Detector backend: {backend}."
        if class_count:
            detail = f"{detail} {class_count} classes loaded."
        return ComponentHealthSchema(
            component="vision",
            label="Vision Engine",
            status=STATUS_OPERATIONAL,
            detail=detail,
        )

    def _decision_component(self) -> ComponentHealthSchema:
        """The decision engine is deterministic and in-process, so it is ready when loaded."""
        return ComponentHealthSchema(
            component="decision",
            label="Decision Engine",
            status=STATUS_OPERATIONAL,
            detail="Deterministic rule engine loaded.",
        )

    def _resource_component(self) -> ComponentHealthSchema:
        """Resource coordination is ready when stock exists to allocate."""
        try:
            count = int(
                self._session.execute(text("SELECT COUNT(*) FROM resources")).scalar_one()
            )
        except SQLAlchemyError:
            return ComponentHealthSchema(
                component="resources",
                label="Resource Coordination",
                status=STATUS_OFFLINE,
                detail="Resource table unavailable.",
            )
        if count == 0:
            return ComponentHealthSchema(
                component="resources",
                label="Resource Coordination",
                status=STATUS_DEGRADED,
                detail="No resources registered; allocations will report shortfalls.",
            )
        return ComponentHealthSchema(
            component="resources",
            label="Resource Coordination",
            status=STATUS_OPERATIONAL,
            detail=f"{count} resources registered.",
        )

    def _api_component(self) -> ComponentHealthSchema:
        """The API is serving by definition if this handler is executing."""
        return ComponentHealthSchema(
            component="api",
            label="API Gateway",
            status=STATUS_OPERATIONAL,
            detail="Serving requests.",
        )
