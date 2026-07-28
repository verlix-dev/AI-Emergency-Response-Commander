"""Database entities for the ARES backend foundation."""

from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampedUUIDMixin
from app.models.enums import IncidentStatus, ResourceStatus, UploadKind


class User(TimestampedUUIDMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    incidents: Mapped[list["Incident"]] = relationship(back_populates="commander")
    action_plans: Mapped[list["ActionPlan"]] = relationship(back_populates="author")
    chat_history: Mapped[list["ChatHistory"]] = relationship(back_populates="user")


class Incident(TimestampedUUIDMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_status_created_at", "status", "created_at"),)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus), default=IncidentStatus.OPEN)
    commander_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    commander: Mapped[User | None] = relationship(back_populates="incidents")
    uploads: Mapped[list["Upload"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    vision_results: Mapped[list["VisionResult"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    reports: Mapped[list["IncidentReport"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    allocations: Mapped[list["Allocation"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    action_plans: Mapped[list["ActionPlan"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    chat_history: Mapped[list["ChatHistory"]] = relationship(back_populates="incident")


class Upload(TimestampedUUIDMixin, Base):
    __tablename__ = "uploads"
    __table_args__ = (CheckConstraint("size_bytes >= 0", name="ck_uploads_size_non_negative"), Index("ix_uploads_incident_id", "incident_id"))

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[UploadKind] = mapped_column(Enum(UploadKind), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    incident: Mapped[Incident] = relationship(back_populates="uploads")
    vision_results: Mapped[list["VisionResult"]] = relationship(back_populates="upload", cascade="all, delete-orphan")


class VisionResult(TimestampedUUIDMixin, Base):
    __tablename__ = "vision_results"
    __table_args__ = (Index("ix_vision_results_incident_id", "incident_id"), Index("ix_vision_results_upload_id", "upload_id"))

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    upload_id: Mapped[UUID] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    incident: Mapped[Incident] = relationship(back_populates="vision_results")
    upload: Mapped[Upload] = relationship(back_populates="vision_results")


class IncidentReport(TimestampedUUIDMixin, Base):
    __tablename__ = "incident_reports"
    __table_args__ = (Index("ix_incident_reports_incident_id", "incident_id"),)

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    incident: Mapped[Incident] = relationship(back_populates="reports")


class Resource(TimestampedUUIDMixin, Base):
    __tablename__ = "resources"
    __table_args__ = (CheckConstraint("quantity >= 0", name="ck_resources_quantity_non_negative"), Index("ix_resources_status", "status"))

    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ResourceStatus] = mapped_column(Enum(ResourceStatus), default=ResourceStatus.AVAILABLE)
    allocations: Mapped[list["Allocation"]] = relationship(back_populates="resource")


class Allocation(TimestampedUUIDMixin, Base):
    __tablename__ = "allocations"
    __table_args__ = (CheckConstraint("quantity >= 1", name="ck_allocations_positive_quantity"), Index("ix_allocations_incident_resource", "incident_id", "resource_id"))

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    incident: Mapped[Incident] = relationship(back_populates="allocations")
    resource: Mapped[Resource] = relationship(back_populates="allocations")


class ActionPlan(TimestampedUUIDMixin, Base):
    __tablename__ = "action_plans"
    __table_args__ = (Index("ix_action_plans_incident_id", "incident_id"),)

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    incident: Mapped[Incident] = relationship(back_populates="action_plans")
    author: Mapped[User | None] = relationship(back_populates="action_plans")


class ChatHistory(TimestampedUUIDMixin, Base):
    __tablename__ = "chat_history"
    __table_args__ = (Index("ix_chat_history_user_created_at", "user_id", "created_at"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    incident_id: Mapped[UUID | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user: Mapped[User] = relationship(back_populates="chat_history")
    incident: Mapped[Incident | None] = relationship(back_populates="chat_history")
