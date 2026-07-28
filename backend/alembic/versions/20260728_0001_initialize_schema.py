"""initialize schema

Revision ID: 20260728_0001
Revises:
Create Date: 2026-07-28 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    incident_status = sa.Enum("OPEN", "RESOLVED", "CLOSED", name="incidentstatus")
    resource_status = sa.Enum("AVAILABLE", "DEPLOYED", "UNAVAILABLE", name="resourcestatus")
    upload_kind = sa.Enum("IMAGE", "VIDEO", "PDF", "TEXT", name="uploadkind")
    op.create_table("users", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("display_name", sa.String(120), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("incidents", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("location", sa.String(300), nullable=False), sa.Column("status", incident_status, nullable=False), sa.Column("commander_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")))
    op.create_index("ix_incidents_status_created_at", "incidents", ["status", "created_at"])
    op.create_table("resources", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("name", sa.String(160), nullable=False, unique=True), sa.Column("resource_type", sa.String(100), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("status", resource_status, nullable=False), sa.CheckConstraint("quantity >= 0", name="ck_resources_quantity_non_negative"))
    op.create_index("ix_resources_status", "resources", ["status"])
    op.create_table("uploads", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("content_type", sa.String(100), nullable=False), sa.Column("kind", upload_kind, nullable=False), sa.Column("size_bytes", sa.Integer(), nullable=False), sa.Column("storage_path", sa.String(512), nullable=False), sa.CheckConstraint("size_bytes >= 0", name="ck_uploads_size_non_negative"))
    op.create_index("ix_uploads_incident_id", "uploads", ["incident_id"])
    op.create_table("vision_results", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False), sa.Column("upload_id", sa.Uuid(), sa.ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False), sa.Column("result", sa.JSON(), nullable=False))
    op.create_index("ix_vision_results_incident_id", "vision_results", ["incident_id"]); op.create_index("ix_vision_results_upload_id", "vision_results", ["upload_id"])
    op.create_table("incident_reports", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False), sa.Column("source", sa.String(100), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("extracted_data", sa.JSON(), nullable=False))
    op.create_index("ix_incident_reports_incident_id", "incident_reports", ["incident_id"])
    op.create_table("allocations", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False), sa.Column("resource_id", sa.Uuid(), sa.ForeignKey("resources.id", ondelete="RESTRICT"), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("rationale", sa.Text()), sa.CheckConstraint("quantity >= 1", name="ck_allocations_positive_quantity"))
    op.create_index("ix_allocations_incident_resource", "allocations", ["incident_id", "resource_id"])
    op.create_table("action_plans", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False), sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("content", sa.JSON(), nullable=False))
    op.create_index("ix_action_plans_incident_id", "action_plans", ["incident_id"])
    op.create_table("chat_history", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="SET NULL")), sa.Column("role", sa.String(32), nullable=False), sa.Column("content", sa.Text(), nullable=False))
    op.create_index("ix_chat_history_user_created_at", "chat_history", ["user_id", "created_at"])


def downgrade() -> None:
    for table in ("chat_history", "action_plans", "allocations", "incident_reports", "vision_results", "uploads", "resources", "incidents", "users"):
        op.drop_table(table)
