"""Persistence access for incidents and their analysis history."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.action_plan import ActionPlan
from app.models.incident import Incident
from app.models.incident_analysis import IncidentAnalysis
from app.models.resource import Resource
from app.models.vision_result import VisionResult


class IncidentRepository:
    """Read and write incidents and their append-only analysis revisions.

    The repository owns queries and flushes but never commits: transaction boundaries belong to
    the caller, so a whole workflow either persists completely or not at all.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_incident(self, incident: Incident) -> Incident:
        """Persist a new incident and populate its generated identifier."""
        self._session.add(incident)
        self._session.flush()
        return incident

    def get_incident(self, incident_id: UUID) -> Incident | None:
        """Return one incident, or ``None`` when it does not exist."""
        return self._session.get(Incident, incident_id)

    def list_incidents(self, limit: int = 50, offset: int = 0) -> list[Incident]:
        """Return incidents newest first, for the operational overview.

        ``created_at`` is written client-side with microsecond precision, so incidents created
        within the same second still order deterministically. The id breaks any residual tie.
        """
        statement = (
            select(Incident)
            .order_by(Incident.created_at.desc(), Incident.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(statement).unique().scalars().all())

    def count_incidents(self) -> int:
        """Return the total number of incidents, for pagination."""
        return int(self._session.execute(select(func.count(Incident.id))).scalar_one())

    def add_analysis(self, analysis: IncidentAnalysis) -> IncidentAnalysis:
        """Append an analysis revision to an incident."""
        self._session.add(analysis)
        self._session.flush()
        return analysis

    def add_vision_result(self, vision_result: VisionResult) -> VisionResult:
        """Record the detections that supported an analysis."""
        self._session.add(vision_result)
        self._session.flush()
        return vision_result

    def add_action_plan(self, action_plan: ActionPlan) -> ActionPlan:
        """Record the commander brief rendered for an analysis."""
        self._session.add(action_plan)
        self._session.flush()
        return action_plan

    def next_revision(self, incident_id: UUID) -> int:
        """Return the revision number the next analysis of this incident should carry."""
        statement = select(func.max(IncidentAnalysis.revision)).where(
            IncidentAnalysis.incident_id == incident_id
        )
        current = self._session.execute(statement).scalar_one_or_none()
        return int(current or 0) + 1

    def list_analyses(self, incident_id: UUID) -> list[IncidentAnalysis]:
        """Return every analysis revision for an incident, oldest first."""
        statement = (
            select(IncidentAnalysis)
            .where(IncidentAnalysis.incident_id == incident_id)
            .order_by(IncidentAnalysis.revision.asc())
        )
        return list(self._session.execute(statement).unique().scalars().all())

    def latest_analysis(self, incident_id: UUID) -> IncidentAnalysis | None:
        """Return the most recent analysis revision for an incident."""
        statement = (
            select(IncidentAnalysis)
            .where(IncidentAnalysis.incident_id == incident_id)
            .order_by(IncidentAnalysis.revision.desc())
            .limit(1)
        )
        return self._session.execute(statement).unique().scalars().first()


class ResourceRepository:
    """Read access to the resource pool offered to the allocation engine."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_available(self) -> list[Resource]:
        """Return every assignable resource in a deterministic order."""
        statement = (
            select(Resource)
            .where(Resource.available.is_(True))
            .order_by(Resource.resource_type.asc(), Resource.resource_name.asc())
        )
        return list(self._session.execute(statement).unique().scalars().all())

    def list_all(self) -> list[Resource]:
        """Return the whole resource pool, available or not, for inventory reporting."""
        statement = select(Resource).order_by(
            Resource.resource_type.asc(), Resource.resource_name.asc()
        )
        return list(self._session.execute(statement).unique().scalars().all())
