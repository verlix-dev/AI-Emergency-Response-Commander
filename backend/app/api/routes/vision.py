from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.dependencies import get_vision_service
from app.core.config import get_settings
from app.engines.models import IncidentAssessment
from app.services.image_intake import ImageIntakeService
from app.vision import VisionService

router = APIRouter(prefix="/vision")


@router.post("/analyze", response_model=IncidentAssessment, status_code=status.HTTP_200_OK)
def analyze_image(
    image: Annotated[UploadFile, File()],
    vision_service: Annotated[VisionService, Depends(get_vision_service)],
) -> IncidentAssessment:
    intake = ImageIntakeService(max_upload_size_mb=get_settings().max_upload_size)
    intake.validate(image.filename, image.content_type)
    with intake.staged(image.file, image.filename) as image_path:
        return vision_service.analyze(image_path)
