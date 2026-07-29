"""Pydantic schemas for action plans."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMResponseSchema


class ActionPlanCreateSchema(BaseModel):
    incident_id: UUID
    generated_plan: str = Field(min_length=1)


class ActionPlanUpdateSchema(BaseModel):
    generated_plan: str | None = Field(default=None, min_length=1)


class ActionPlanResponseSchema(ORMResponseSchema):
    id: UUID
    incident_id: UUID
    generated_plan: str
    created_at: datetime
