"""Pydantic schemas for incident chat history."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMResponseSchema


class ChatHistoryCreateSchema(BaseModel):
    incident_id: UUID
    role: str = Field(min_length=1, max_length=32)
    message: str = Field(min_length=1)


class ChatHistoryUpdateSchema(BaseModel):
    role: str | None = Field(default=None, min_length=1, max_length=32)
    message: str | None = Field(default=None, min_length=1)


class ChatHistoryResponseSchema(ORMResponseSchema):
    id: UUID
    incident_id: UUID
    role: str
    message: str
    created_at: datetime
