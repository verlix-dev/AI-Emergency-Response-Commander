"""Incident root entity."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import UUIDPrimaryKeyMixin
from app.models.enums import IncidentStatus


def _utcnow() -> datetime:
    """Return an aware timestamp with microsecond precision.

    Applied client-side so that incidents created within the same second still order
    deterministically; the database ``now()`` default only resolves to whole seconds.
    """
    return datetime.now(timezone.utc)


class Incident(UUIDPrimaryKeyMixin, Base):
    """A reported emergency and the aggregate root for incident data."""

    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_status_priority", "status", "priority"),)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    incident_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus), nullable=False)
    priority: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(300), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now(), onupdate=_utcnow)

    uploads: Mapped[list["Upload"]] = relationship(back_populates="incident", cascade="all, delete-orphan", lazy="selectin")
    vision_results: Mapped[list["VisionResult"]] = relationship(back_populates="incident", cascade="all, delete-orphan", lazy="selectin")
    incident_reports: Mapped[list["IncidentReport"]] = relationship(back_populates="incident", cascade="all, delete-orphan", lazy="selectin")
    action_plans: Mapped[list["ActionPlan"]] = relationship(back_populates="incident", cascade="all, delete-orphan", lazy="selectin")
    chat_history: Mapped[list["ChatHistory"]] = relationship(back_populates="incident", cascade="all, delete-orphan", lazy="selectin")
    analyses: Mapped[list["IncidentAnalysis"]] = relationship(back_populates="incident", cascade="all, delete-orphan", lazy="selectin")
