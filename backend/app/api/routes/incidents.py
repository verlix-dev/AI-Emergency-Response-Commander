from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_incident_service
from app.schemas.entities import IncidentCreateSchema, IncidentResponseSchema, IncidentUpdateSchema
from app.services import IncidentService

router = APIRouter(prefix="/incidents")

@router.post("", response_model=IncidentResponseSchema, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreateSchema, service: IncidentService = Depends(get_incident_service)): return service.create(payload)
@router.get("", response_model=list[IncidentResponseSchema])
def list_incidents(service: IncidentService = Depends(get_incident_service)): return service.list()
@router.get("/{incident_id}", response_model=IncidentResponseSchema)
def get_incident(incident_id: UUID, service: IncidentService = Depends(get_incident_service)): return service.get(incident_id)
@router.patch("/{incident_id}", response_model=IncidentResponseSchema)
def update_incident(incident_id: UUID, payload: IncidentUpdateSchema, service: IncidentService = Depends(get_incident_service)): return service.update(incident_id, payload)
@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: UUID, service: IncidentService = Depends(get_incident_service)) -> Response:
    service.delete(incident_id); return Response(status_code=status.HTTP_204_NO_CONTENT)
