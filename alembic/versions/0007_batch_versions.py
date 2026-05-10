"""add batch processing versions

Revision ID: 0007_batch_versions
Revises: 0006_adjustment_versions
Create Date: 2026-05-10 23:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_batch_versions"
down_revision: Union[str, None] = "0006_adjustment_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("processing_jobs", sa.Column("version_number", sa.Integer(), nullable=True))
    op.add_column("processing_jobs", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "processing_jobs",
        sa.Column("retry_scope", sa.String(length=32), nullable=False, server_default="none"),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("retry_of_job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_processing_jobs_retry_of_job_id",
        "processing_jobs",
        "processing_jobs",
        ["retry_of_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        WITH numbered AS (
            SELECT id, row_number() OVER (PARTITION BY project_id ORDER BY created_at, id)::integer AS version_number
            FROM processing_jobs
        )
        UPDATE processing_jobs
        SET version_number = numbered.version_number
        FROM numbered
        WHERE processing_jobs.id = numbered.id
        """
    )
    op.alter_column("processing_jobs", "version_number", nullable=False)
    op.create_unique_constraint(
        "uq_processing_job_project_version",
        "processing_jobs",
        ["project_id", "version_number"],
    )

    op.create_table(
        "photo_processing_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("photo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processing_job_id"], ["processing_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("processing_job_id", "photo_id", name="uq_photo_processing_job_photo"),
    )
    op.create_index(op.f("ix_photo_processing_versions_photo_id"), "photo_processing_versions", ["photo_id"], unique=False)
    op.create_index(
        op.f("ix_photo_processing_versions_processing_job_id"),
        "photo_processing_versions",
        ["processing_job_id"],
        unique=False,
    )

    op.add_column("exports", sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "exports",
        sa.Column("allow_partial", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_foreign_key(
        "fk_exports_processing_job_id",
        "exports",
        "processing_jobs",
        ["processing_job_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_exports_processing_job_id", "exports", type_="foreignkey")
    op.drop_column("exports", "allow_partial")
    op.drop_column("exports", "processing_job_id")

    op.drop_index(op.f("ix_photo_processing_versions_processing_job_id"), table_name="photo_processing_versions")
    op.drop_index(op.f("ix_photo_processing_versions_photo_id"), table_name="photo_processing_versions")
    op.drop_table("photo_processing_versions")

    op.drop_constraint("uq_processing_job_project_version", "processing_jobs", type_="unique")
    op.drop_constraint("fk_processing_jobs_retry_of_job_id", "processing_jobs", type_="foreignkey")
    op.drop_column("processing_jobs", "retry_of_job_id")
    op.drop_column("processing_jobs", "retry_scope")
    op.drop_column("processing_jobs", "archived_at")
    op.drop_column("processing_jobs", "version_number")
