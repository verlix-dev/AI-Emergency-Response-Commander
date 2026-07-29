"""Stored vision-analysis result model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class VisionResult(UUIDPrimaryKeyMixin, Base):
    """Structured visual observations for an incident."""

    __tablename__ = "vision_results"
    __table_args__ = (
        CheckConstraint("people_detected >= 0", name="ck_vision_results_people_non_negative"),
        CheckConstraint("vehicles_detected >= 0", name="ck_vision_results_vehicles_non_negative"),
        CheckConstraint("boats_detected >= 0", name="ck_vision_results_boats_non_negative"),
        CheckConstraint("collapsed_structures >= 0", name="ck_vision_results_structures_non_negative"),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="ck_vision_results_confidence_range"),
        Index("ix_vision_results_incident_id", "incident_id"),
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    people_detected: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicles_detected: Mapped[int] = mapped_column(Integer, nullable=False)
    boats_detected: Mapped[int] = mapped_column(Integer, nullable=False)
    collapsed_structures: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="vision_results", lazy="joined")
