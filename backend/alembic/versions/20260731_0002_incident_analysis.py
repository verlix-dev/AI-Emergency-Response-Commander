"""create incident analysis table

Revision ID: 20260731_0002
Revises: 20260728_0001
Create Date: 2026-07-31 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260731_0002"
down_revision: Union[str, Sequence[str], None] = "20260728_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incident_analyses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("severity_level", sa.String(length=50), nullable=False),
        sa.Column("severity_score", sa.Float(), nullable=False),
        sa.Column("priority_level", sa.String(length=50), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("assessment", sa.JSON(), nullable=False),
        sa.Column("decision", sa.JSON(), nullable=False),
        sa.Column("resources", sa.JSON(), nullable=False),
        sa.Column("commander_brief", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_incident_analyses_revision_positive"),
        sa.CheckConstraint("severity_score >= 0 AND severity_score <= 100", name="ck_incident_analyses_severity_score_range"),
        sa.CheckConstraint("priority_score >= 0 AND priority_score <= 100", name="ck_incident_analyses_priority_score_range"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_incident_analyses_confidence_range"),
    )
    op.create_index("ix_incident_analyses_incident_revision", "incident_analyses", ["incident_id", "revision"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_incident_analyses_incident_revision", table_name="incident_analyses")
    op.drop_table("incident_analyses")
