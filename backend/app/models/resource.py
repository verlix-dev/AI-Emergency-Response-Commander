"""Emergency resource persistence model."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import UUIDPrimaryKeyMixin


class Resource(UUIDPrimaryKeyMixin, Base):
    """An independently tracked emergency-response resource."""

    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint("capacity IS NULL OR capacity >= 0", name="ck_resources_capacity_non_negative"),
        Index("ix_resources_status_available", "status", "available"),
    )

    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    current_location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
