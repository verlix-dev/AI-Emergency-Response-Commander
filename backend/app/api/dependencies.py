from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.repositories import ActionPlanRepository, ChatRepository, IncidentRepository, ResourceRepository, UploadRepository
from app.services import ActionPlanService, ChatService, IncidentService, ResourceService, UploadService

def get_incident_service(session: Session = Depends(get_db_session)) -> IncidentService: return IncidentService(IncidentRepository(session))
def get_upload_service(session: Session = Depends(get_db_session)) -> UploadService: return UploadService(UploadRepository(session))
def get_resource_service(session: Session = Depends(get_db_session)) -> ResourceService: return ResourceService(ResourceRepository(session))
def get_action_plan_service(session: Session = Depends(get_db_session)) -> ActionPlanService: return ActionPlanService(ActionPlanRepository(session))
def get_chat_service(session: Session = Depends(get_db_session)) -> ChatService: return ChatService(ChatRepository(session))
