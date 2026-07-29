"""Action plan persistence model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class ActionPlan(UUIDPrimaryKeyMixin, Base):
    """A stored action plan associated with an incident."""

    __tablename__ = "action_plans"
    __table_args__ = (Index("ix_action_plans_incident_id", "incident_id"),)

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    generated_plan: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="action_plans", lazy="joined")
