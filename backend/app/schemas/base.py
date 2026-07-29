"""Shared Pydantic configuration for ORM response schemas."""

from pydantic import BaseModel, ConfigDict


class ORMResponseSchema(BaseModel):
    """Enable Pydantic v2 validation from SQLAlchemy model attributes."""

    model_config = ConfigDict(from_attributes=True)
