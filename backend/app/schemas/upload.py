"""Pydantic schemas for uploads."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMResponseSchema


class UploadCreateSchema(BaseModel):
    incident_id: UUID
    file_name: str = Field(min_length=1, max_length=255)
    file_type: str = Field(min_length=1, max_length=100)
    file_path: str = Field(min_length=1, max_length=1024)
    file_size: int = Field(ge=0)


class UploadUpdateSchema(BaseModel):
    file_name: str | None = Field(default=None, min_length=1, max_length=255)
    file_type: str | None = Field(default=None, min_length=1, max_length=100)
    file_path: str | None = Field(default=None, min_length=1, max_length=1024)
    file_size: int | None = Field(default=None, ge=0)


class UploadResponseSchema(ORMResponseSchema):
    id: UUID
    incident_id: UUID
    file_name: str
    file_type: str
    file_path: str
    file_size: int
    uploaded_at: datetime
