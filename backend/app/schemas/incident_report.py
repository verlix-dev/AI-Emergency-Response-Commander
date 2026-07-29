"""Pydantic schemas for incident reports."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMResponseSchema


class IncidentReportCreateSchema(BaseModel):
    incident_id: UUID
    summary: str = Field(min_length=1)
    location: str | None = Field(default=None, max_length=300)
    victim_count: int | None = Field(default=None, ge=0)
    road_status: str | None = Field(default=None, max_length=100)
    requested_resources: dict[str, Any] | None = None


class IncidentReportUpdateSchema(BaseModel):
    summary: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, max_length=300)
    victim_count: int | None = Field(default=None, ge=0)
    road_status: str | None = Field(default=None, max_length=100)
    requested_resources: dict[str, Any] | None = None


class IncidentReportResponseSchema(ORMResponseSchema):
    id: UUID
    incident_id: UUID
    summary: str
    location: str | None
    victim_count: int | None
    road_status: str | None
    requested_resources: dict[str, Any] | None
    created_at: datetime
