from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IncidentStatus, ResourceStatus, UploadKind
from app.schemas.common import ResponseSchema


class UserCreateSchema(BaseModel): email: str; display_name: str
class UserUpdateSchema(BaseModel): email: str | None = None; display_name: str | None = None
class UserResponseSchema(ResponseSchema): email: str; display_name: str

class IncidentCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=300)
    description: str | None = None
    commander_id: UUID | None = None
class IncidentUpdateSchema(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: IncidentStatus | None = None
class IncidentResponseSchema(ResponseSchema): title: str; location: str; description: str | None; status: IncidentStatus; commander_id: UUID | None

class UploadCreateSchema(BaseModel):
    incident_id: UUID
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    kind: UploadKind
    size_bytes: int = Field(ge=0)
    storage_path: str = Field(min_length=1, max_length=512)
class UploadUpdateSchema(BaseModel): filename: str | None = Field(default=None, min_length=1, max_length=255); storage_path: str | None = Field(default=None, min_length=1, max_length=512)
class UploadResponseSchema(ResponseSchema): incident_id: UUID; filename: str; content_type: str; kind: UploadKind; size_bytes: int; storage_path: str

class VisionResultCreateSchema(BaseModel): incident_id: UUID; upload_id: UUID; result: dict[str, Any] = Field(default_factory=dict)
class VisionResultUpdateSchema(BaseModel): result: dict[str, Any] | None = None
class VisionResultResponseSchema(ResponseSchema): incident_id: UUID; upload_id: UUID; result: dict[str, Any]

class IncidentReportCreateSchema(BaseModel): incident_id: UUID; source: str = Field(min_length=1, max_length=100); body: str = Field(min_length=1); extracted_data: dict[str, Any] = Field(default_factory=dict)
class IncidentReportUpdateSchema(BaseModel): source: str | None = Field(default=None, min_length=1, max_length=100); body: str | None = Field(default=None, min_length=1); extracted_data: dict[str, Any] | None = None
class IncidentReportResponseSchema(ResponseSchema): incident_id: UUID; source: str; body: str; extracted_data: dict[str, Any]

class ResourceCreateSchema(BaseModel): name: str = Field(min_length=1, max_length=160); resource_type: str = Field(min_length=1, max_length=100); quantity: int = Field(ge=0); status: ResourceStatus = ResourceStatus.AVAILABLE
class ResourceUpdateSchema(BaseModel): name: str | None = Field(default=None, min_length=1, max_length=160); resource_type: str | None = Field(default=None, min_length=1, max_length=100); quantity: int | None = Field(default=None, ge=0); status: ResourceStatus | None = None
class ResourceResponseSchema(ResponseSchema): name: str; resource_type: str; quantity: int; status: ResourceStatus

class AllocationCreateSchema(BaseModel): incident_id: UUID; resource_id: UUID; quantity: int = Field(ge=1); rationale: str | None = None
class AllocationUpdateSchema(BaseModel): quantity: int | None = Field(default=None, ge=1); rationale: str | None = None
class AllocationResponseSchema(ResponseSchema): incident_id: UUID; resource_id: UUID; quantity: int; rationale: str | None

class ActionPlanCreateSchema(BaseModel): incident_id: UUID; author_id: UUID | None = None; content: dict[str, Any] = Field(default_factory=dict)
class ActionPlanUpdateSchema(BaseModel): content: dict[str, Any] | None = None
class ActionPlanResponseSchema(ResponseSchema): incident_id: UUID; author_id: UUID | None; content: dict[str, Any]

class ChatHistoryCreateSchema(BaseModel): user_id: UUID; incident_id: UUID | None = None; role: str = Field(min_length=1, max_length=32); content: str = Field(min_length=1)
class ChatHistoryUpdateSchema(BaseModel): content: str | None = Field(default=None, min_length=1)
class ChatHistoryResponseSchema(ResponseSchema): user_id: UUID; incident_id: UUID | None; role: str; content: str
