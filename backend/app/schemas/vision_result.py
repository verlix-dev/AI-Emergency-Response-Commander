"""Pydantic schemas for vision results."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMResponseSchema


class VisionResultCreateSchema(BaseModel):
    incident_id: UUID
    people_detected: int = Field(ge=0)
    vehicles_detected: int = Field(ge=0)
    boats_detected: int = Field(ge=0)
    collapsed_structures: int = Field(ge=0)
    confidence_score: float = Field(ge=0, le=1)


class VisionResultUpdateSchema(BaseModel):
    people_detected: int | None = Field(default=None, ge=0)
    vehicles_detected: int | None = Field(default=None, ge=0)
    boats_detected: int | None = Field(default=None, ge=0)
    collapsed_structures: int | None = Field(default=None, ge=0)
    confidence_score: float | None = Field(default=None, ge=0, le=1)


class VisionResultResponseSchema(ORMResponseSchema):
    id: UUID
    incident_id: UUID
    people_detected: int
    vehicles_detected: int
    boats_detected: int
    collapsed_structures: int
    confidence_score: float
    created_at: datetime
