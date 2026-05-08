"""add adjustment versions

Revision ID: 0006_adjustment_versions
Revises: 0005_adjustment_jobs
Create Date: 2026-05-08 08:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_adjustment_versions"
down_revision: Union[str, None] = "0005_adjustment_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "photo_adjustment_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("photo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("photo_id", "version_number", name="uq_adjustment_version_photo_number"),
    )
    op.create_index(
        op.f("ix_photo_adjustment_versions_photo_id"),
        "photo_adjustment_versions",
        ["photo_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_photo_adjustment_versions_photo_id"), table_name="photo_adjustment_versions")
    op.drop_table("photo_adjustment_versions")
