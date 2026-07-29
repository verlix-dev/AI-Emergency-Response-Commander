"""Pydantic schemas for incidents."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import IncidentStatus
from app.schemas.base import ORMResponseSchema


class IncidentCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    incident_type: str = Field(min_length=1, max_length=100)
    status: IncidentStatus
    priority: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=300)
    latitude: float | None = None
    longitude: float | None = None


class IncidentUpdateSchema(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    incident_type: str | None = Field(default=None, min_length=1, max_length=100)
    status: IncidentStatus | None = None
    priority: str | None = Field(default=None, min_length=1, max_length=50)
    location: str | None = Field(default=None, min_length=1, max_length=300)
    latitude: float | None = None
    longitude: float | None = None


class IncidentResponseSchema(ORMResponseSchema):
    id: UUID
    title: str
    description: str | None
    incident_type: str
    status: IncidentStatus
    priority: str
    location: str
    latitude: float | None
    longitude: float | None
    created_at: datetime
    updated_at: datetime
