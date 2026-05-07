"""processing pipeline: processing_jobs + photos.processed_paths

Revision ID: 0002_processing_pipeline
Revises: 0001_initial
Create Date: 2026-05-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_processing_pipeline"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    color_grade_preset = postgresql.ENUM(
        "showroom_white",
        "outdoor_warm",
        "night_cold",
        name="color_grade_preset",
        create_type=False,
    )
    color_grade_preset.create(bind, checkfirst=True)

    aspect_ratio = postgresql.ENUM(
        "original",
        "ratio_3_2",
        "ratio_4_3",
        "ratio_16_9",
        "ratio_1_1",
        "ratio_9_16",
        name="aspect_ratio",
        create_type=False,
    )
    aspect_ratio.create(bind, checkfirst=True)

    denoise_strength = postgresql.ENUM(
        "none",
        "light",
        "medium",
        "heavy",
        name="denoise_strength",
        create_type=False,
    )
    denoise_strength.create(bind, checkfirst=True)

    processing_job_status = postgresql.ENUM(
        "pending",
        "running",
        "done",
        "failed",
        name="processing_job_status",
        create_type=False,
    )
    processing_job_status.create(bind, checkfirst=True)

    op.add_column(
        "photos",
        sa.Column(
            "processed_paths",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            processing_job_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("preset", color_grade_preset, nullable=False),
        sa.Column(
            "denoise_strength",
            denoise_strength,
            nullable=False,
            server_default="none",
        ),
        sa.Column(
            "lens_distort_correct",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "level_correct",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("auto_crop_aspect", aspect_ratio, nullable=True),
        sa.Column(
            "photo_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
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


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_processing_jobs_project_id", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_column("photos", "processed_paths")
    sa.Enum(name="processing_job_status").drop(bind, checkfirst=True)
    sa.Enum(name="denoise_strength").drop(bind, checkfirst=True)
    sa.Enum(name="aspect_ratio").drop(bind, checkfirst=True)
    sa.Enum(name="color_grade_preset").drop(bind, checkfirst=True)
