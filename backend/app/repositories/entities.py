from sqlalchemy.orm import Session

from app.models import ActionPlan, ChatHistory, Incident, Resource, Upload, VisionResult
from app.repositories.base import BaseRepository

class IncidentRepository(BaseRepository[Incident]):
    def __init__(self, session: Session) -> None: super().__init__(session, Incident)
class UploadRepository(BaseRepository[Upload]):
    def __init__(self, session: Session) -> None: super().__init__(session, Upload)
class ResourceRepository(BaseRepository[Resource]):
    def __init__(self, session: Session) -> None: super().__init__(session, Resource)
class ActionPlanRepository(BaseRepository[ActionPlan]):
    def __init__(self, session: Session) -> None: super().__init__(session, ActionPlan)
class VisionRepository(BaseRepository[VisionResult]):
    def __init__(self, session: Session) -> None: super().__init__(session, VisionResult)
class ChatRepository(BaseRepository[ChatHistory]):
    def __init__(self, session: Session) -> None: super().__init__(session, ChatHistory)
