from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_incident_analysis_service, get_operations_service
from app.core.config import get_settings
from app.database.session import get_db_session
from app.schemas.analysis import (
    IncidentAnalysisResponse,
    IncidentListResponse,
    IncidentTimelineResponse,
)
from app.services.image_intake import ImageIntakeService
from app.services.incident_analysis import IncidentAnalysisService
from app.services.operations import OperationsService

router = APIRouter(prefix="/incidents")


@router.get("", response_model=IncidentListResponse, status_code=status.HTTP_200_OK)
def list_incidents(
    service: Annotated[OperationsService, Depends(get_operations_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> IncidentListResponse:
    return service.list_incidents(limit=limit, offset=offset)


@router.post("/analyze", response_model=IncidentAnalysisResponse, status_code=status.HTTP_201_CREATED)
def analyze_incident(
    image: Annotated[UploadFile, File()],
    service: Annotated[IncidentAnalysisService, Depends(get_incident_analysis_service)],
    session: Annotated[Session, Depends(get_db_session)],
    location: Annotated[str | None, Form()] = None,
    latitude: Annotated[float | None, Form()] = None,
    longitude: Annotated[float | None, Form()] = None,
    title: Annotated[str | None, Form()] = None,
) -> IncidentAnalysisResponse:
    intake = ImageIntakeService(max_upload_size_mb=get_settings().max_upload_size)
    intake.validate(image.filename, image.content_type)
    with intake.staged(image.file, image.filename) as image_path:
        response = service.analyze_image(
            image_path=image_path,
            location=location,
            latitude=latitude,
            longitude=longitude,
            title=title,
        )
    session.commit()
    return response


@router.post(
    "/{incident_id}/analyze",
    response_model=IncidentAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def reanalyze_incident(
    incident_id: UUID,
    image: Annotated[UploadFile, File()],
    service: Annotated[IncidentAnalysisService, Depends(get_incident_analysis_service)],
    session: Annotated[Session, Depends(get_db_session)],
) -> IncidentAnalysisResponse:
    intake = ImageIntakeService(max_upload_size_mb=get_settings().max_upload_size)
    intake.validate(image.filename, image.content_type)
    with intake.staged(image.file, image.filename) as image_path:
        response = service.reanalyze_incident(incident_id=incident_id, image_path=image_path)
    session.commit()
    return response


@router.get(
    "/{incident_id}/timeline",
    response_model=IncidentTimelineResponse,
    status_code=status.HTTP_200_OK,
)
def get_incident_timeline(
    incident_id: UUID,
    service: Annotated[IncidentAnalysisService, Depends(get_incident_analysis_service)],
) -> IncidentTimelineResponse:
    return service.get_timeline(incident_id)
