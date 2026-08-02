from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_resource_inventory_service, get_system_status_service
from app.schemas.analysis import ResourceInventoryResponse, SystemStatusResponse
from app.services.operations import ResourceInventoryService, SystemStatusService

router = APIRouter()


@router.get(
    "/resources/inventory",
    response_model=ResourceInventoryResponse,
    status_code=status.HTTP_200_OK,
)
def get_resource_inventory(
    service: Annotated[ResourceInventoryService, Depends(get_resource_inventory_service)],
) -> ResourceInventoryResponse:
    return service.get_inventory()


@router.get("/system/status", response_model=SystemStatusResponse, status_code=status.HTTP_200_OK)
def get_system_status(
    service: Annotated[SystemStatusService, Depends(get_system_status_service)],
) -> SystemStatusResponse:
    return service.get_status()
