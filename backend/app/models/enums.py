from enum import StrEnum


class IncidentStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ResourceStatus(StrEnum):
    AVAILABLE = "available"
    DEPLOYED = "deployed"
    UNAVAILABLE = "unavailable"


class UploadKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    PDF = "pdf"
    TEXT = "text"
