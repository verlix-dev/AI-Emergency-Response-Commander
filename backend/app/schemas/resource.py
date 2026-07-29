"""Pydantic schemas for resources."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMResponseSchema


class ResourceCreateSchema(BaseModel):
    resource_type: str = Field(min_length=1, max_length=100)
    resource_name: str = Field(min_length=1, max_length=160)
    status: str = Field(min_length=1, max_length=100)
    current_location: str | None = Field(default=None, max_length=300)
    capacity: int | None = Field(default=None, ge=0)
    available: bool


class ResourceUpdateSchema(BaseModel):
    resource_type: str | None = Field(default=None, min_length=1, max_length=100)
    resource_name: str | None = Field(default=None, min_length=1, max_length=160)
    status: str | None = Field(default=None, min_length=1, max_length=100)
    current_location: str | None = Field(default=None, max_length=300)
    capacity: int | None = Field(default=None, ge=0)
    available: bool | None = None


class ResourceResponseSchema(ORMResponseSchema):
    id: UUID
    resource_type: str
    resource_name: str
    status: str
    current_location: str | None
    capacity: int | None
    available: bool
    created_at: datetime
