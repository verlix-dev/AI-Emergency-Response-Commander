"""Incident report persistence model."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class IncidentReport(UUIDPrimaryKeyMixin, Base):
    """A structured report associated with an incident."""

    __tablename__ = "incident_reports"
    __table_args__ = (
        CheckConstraint("victim_count IS NULL OR victim_count >= 0", name="ck_incident_reports_victim_count_non_negative"),
        Index("ix_incident_reports_incident_id", "incident_id"),
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    victim_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    road_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    requested_resources: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="incident_reports", lazy="joined")
