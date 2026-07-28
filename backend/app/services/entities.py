from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.exceptions import ApplicationError, NotFoundError
from app.repositories import ActionPlanRepository, ChatRepository, IncidentRepository, ResourceRepository, UploadRepository
from app.schemas.entities import ActionPlanCreateSchema, ChatHistoryCreateSchema, IncidentCreateSchema, IncidentUpdateSchema, ResourceCreateSchema, UploadCreateSchema


class IncidentService:
    def __init__(self, repository: IncidentRepository) -> None: self.repository = repository; self.logger = get_logger(__name__)
    def create(self, payload: IncidentCreateSchema):
        entity = self.repository.create(payload.model_dump()); self.logger.info("incident_created id=%s", entity.id); return entity
    def list(self): return self.repository.list()
    def get(self, entity_id: UUID):
        entity = self.repository.get(entity_id)
        if entity is None: raise NotFoundError("Incident was not found.")
        return entity
    def update(self, entity_id: UUID, payload: IncidentUpdateSchema): return self.repository.update(self.get(entity_id), payload.model_dump(exclude_unset=True))
    def delete(self, entity_id: UUID) -> None: self.repository.delete(self.get(entity_id)); self.logger.info("incident_deleted id=%s", entity_id)


class UploadService:
    def __init__(self, repository: UploadRepository) -> None: self.repository = repository; self.logger = get_logger(__name__)
    def create(self, payload: UploadCreateSchema):
        if payload.size_bytes > get_settings().max_upload_size: raise ApplicationError("Upload exceeds the configured maximum size.")
        entity = self.repository.create(payload.model_dump()); self.logger.info("upload_registered id=%s", entity.id); return entity


class ResourceService:
    def __init__(self, repository: ResourceRepository) -> None: self.repository = repository; self.logger = get_logger(__name__)
    def create(self, payload: ResourceCreateSchema):
        entity = self.repository.create(payload.model_dump()); self.logger.info("resource_created id=%s", entity.id); return entity
    def list(self): return self.repository.list()


class ActionPlanService:
    def __init__(self, repository: ActionPlanRepository) -> None: self.repository = repository; self.logger = get_logger(__name__)
    def create(self, payload: ActionPlanCreateSchema):
        entity = self.repository.create(payload.model_dump()); self.logger.info("action_plan_created id=%s", entity.id); return entity


class ChatService:
    def __init__(self, repository: ChatRepository) -> None: self.repository = repository; self.logger = get_logger(__name__)
    def create(self, payload: ChatHistoryCreateSchema):
        entity = self.repository.create(payload.model_dump()); self.logger.info("chat_history_created id=%s", entity.id); return entity
