"""Persisted analysis-revision model."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class IncidentAnalysis(UUIDPrimaryKeyMixin, Base):
    """One completed end-to-end analysis of an incident.

    Records are append-only: each new analysis of the same incident is a fresh revision rather
    than an update, so the incident's history remains an auditable record of what was known and
    decided at each point.
    """

    __tablename__ = "incident_analyses"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_incident_analyses_revision_positive"),
        CheckConstraint(
            "severity_score >= 0 AND severity_score <= 100",
            name="ck_incident_analyses_severity_score_range",
        ),
        CheckConstraint(
            "priority_score >= 0 AND priority_score <= 100",
            name="ck_incident_analyses_priority_score_range",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_incident_analyses_confidence_range"
        ),
        Index("ix_incident_analyses_incident_revision", "incident_id", "revision", unique=True),
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    severity_level: Mapped[str] = mapped_column(String(50), nullable=False)
    severity_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_level: Mapped[str] = mapped_column(String(50), nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    assessment: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    decision: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    resources: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    commander_brief: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="analyses", lazy="joined")
