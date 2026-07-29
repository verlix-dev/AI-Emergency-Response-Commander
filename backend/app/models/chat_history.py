"""Incident chat-history persistence model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class ChatHistory(UUIDPrimaryKeyMixin, Base):
    """A chat message retained in an incident context."""

    __tablename__ = "chat_history"
    __table_args__ = (Index("ix_chat_history_incident_created_at", "incident_id", "created_at"),)

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident: Mapped["Incident"] = relationship(back_populates="chat_history", lazy="joined")
