"""v0.2.0: processing_jobs + photos.processed_paths

Revision ID: 0002_processing_jobs
Revises: 0001_initial
Create Date: 2026-05-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_processing_jobs"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    color_grade_preset = postgresql.ENUM(
        "showroom_white",
        "outdoor_warm",
        "night_cold",
        name="color_grade_preset",
        create_type=False,
    )
    color_grade_preset.create(op.get_bind(), checkfirst=True)

    processing_status = postgresql.ENUM(
        "pending",
        "running",
        "done",
        "failed",
        name="processing_job_status",
        create_type=False,
    )
    processing_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("preset", color_grade_preset, nullable=False),
        sa.Column("level_correct", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "auto_crop_aspect",
            sa.String(16),
            nullable=False,
            server_default="original",
        ),
        sa.Column(
            "status",
            processing_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("progress_done", sa.Integer, nullable=False, server_default="0"),
        sa.Column("progress_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_processing_jobs_project_id", "processing_jobs", ["project_id"]
    )

    op.add_column(
        "photos",
        sa.Column(
            "processed_paths",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("photos", "processed_paths")
    op.drop_index("ix_processing_jobs_project_id", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    sa.Enum(name="processing_job_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="color_grade_preset").drop(op.get_bind(), checkfirst=True)
