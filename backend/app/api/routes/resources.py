from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_resource_service
from app.schemas.entities import ResourceCreateSchema, ResourceResponseSchema
from app.services import ResourceService

router = APIRouter(prefix="/resources")

@router.get("", response_model=list[ResourceResponseSchema])
def list_resources(service: ResourceService = Depends(get_resource_service)): return service.list()
@router.post("", response_model=ResourceResponseSchema, status_code=status.HTTP_201_CREATED)
def create_resource(payload: ResourceCreateSchema, service: ResourceService = Depends(get_resource_service)): return service.create(payload)
