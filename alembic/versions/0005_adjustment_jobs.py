"""add adjustment jobs

Revision ID: 0005_adjustment_jobs
Revises: 0004_adjustment_panel
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_adjustment_jobs"
down_revision: str | None = "0004_adjustment_panel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    processing_job_status = postgresql.ENUM(
        "pending",
        "running",
        "done",
        "failed",
        name="processing_job_status",
        create_type=False,
    )
    op.create_table(
        "adjustment_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", processing_job_status, nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("photo_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adjustment_jobs_project_id", "adjustment_jobs", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_adjustment_jobs_project_id", table_name="adjustment_jobs")
    op.drop_table("adjustment_jobs")
