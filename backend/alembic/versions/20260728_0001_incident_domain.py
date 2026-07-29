"""create incident domain tables

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
    incident_status = sa.Enum("CREATED", "ANALYZING", "PLANNED", "RESPONDING", "RESOLVED", "CLOSED", name="incidentstatus")
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("incident_type", sa.String(length=100), nullable=False),
        sa.Column("status", incident_status, nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("location", sa.String(length=300), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_incidents_status_priority", "incidents", ["status", "priority"])
    op.create_table(
        "uploads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=100), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("file_size >= 0", name="ck_uploads_file_size_non_negative"),
    )
    op.create_index("ix_uploads_incident_id", "uploads", ["incident_id"])
    op.create_table(
        "vision_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("people_detected", sa.Integer(), nullable=False),
        sa.Column("vehicles_detected", sa.Integer(), nullable=False),
        sa.Column("boats_detected", sa.Integer(), nullable=False),
        sa.Column("collapsed_structures", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("people_detected >= 0", name="ck_vision_results_people_non_negative"),
        sa.CheckConstraint("vehicles_detected >= 0", name="ck_vision_results_vehicles_non_negative"),
        sa.CheckConstraint("boats_detected >= 0", name="ck_vision_results_boats_non_negative"),
        sa.CheckConstraint("collapsed_structures >= 0", name="ck_vision_results_structures_non_negative"),
        sa.CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="ck_vision_results_confidence_range"),
    )
    op.create_index("ix_vision_results_incident_id", "vision_results", ["incident_id"])
    op.create_table(
        "incident_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=300), nullable=True),
        sa.Column("victim_count", sa.Integer(), nullable=True),
        sa.Column("road_status", sa.String(length=100), nullable=True),
        sa.Column("requested_resources", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("victim_count IS NULL OR victim_count >= 0", name="ck_incident_reports_victim_count_non_negative"),
    )
    op.create_index("ix_incident_reports_incident_id", "incident_reports", ["incident_id"])
    op.create_table(
        "resources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column("current_location", sa.String(length=300), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("capacity IS NULL OR capacity >= 0", name="ck_resources_capacity_non_negative"),
    )
    op.create_index("ix_resources_status_available", "resources", ["status", "available"])
    op.create_table(
        "action_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generated_plan", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_action_plans_incident_id", "action_plans", ["incident_id"])
    op.create_table(
        "chat_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_chat_history_incident_created_at", "chat_history", ["incident_id", "created_at"])


def downgrade() -> None:
    op.drop_table("chat_history")
    op.drop_table("action_plans")
    op.drop_table("resources")
    op.drop_table("incident_reports")
    op.drop_table("vision_results")
    op.drop_table("uploads")
    op.drop_table("incidents")
