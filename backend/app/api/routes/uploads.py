from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_upload_service
from app.schemas.entities import UploadCreateSchema, UploadResponseSchema
from app.services import UploadService

router = APIRouter(prefix="/uploads")

@router.post("", response_model=UploadResponseSchema, status_code=status.HTTP_201_CREATED)
def create_upload(payload: UploadCreateSchema, service: UploadService = Depends(get_upload_service)): return service.create(payload)
