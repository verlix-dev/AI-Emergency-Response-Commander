from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Database-only operations shared by concrete repositories."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session, self.model = session, model

    def get(self, entity_id: UUID) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def list(self) -> list[ModelT]:
        return list(self.session.scalars(select(self.model)))

    def create(self, values: dict) -> ModelT:
        try:
            entity = self.model(**values)
            self.session.add(entity); self.session.commit(); self.session.refresh(entity)
            return entity
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def update(self, entity: ModelT, values: dict) -> ModelT:
        try:
            for name, value in values.items(): setattr(entity, name, value)
            self.session.commit(); self.session.refresh(entity)
            return entity
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def delete(self, entity: ModelT) -> None:
        try:
            self.session.delete(entity); self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
