"""initial schema: projects / photos / exports

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_path", sa.String(512), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("mime_type", sa.String(64), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_photos_project_id", "photos", ["project_id"])

    export_status = postgresql.ENUM(
        "pending", "running", "done", "failed", name="export_status", create_type=False
    )
    export_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            export_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("zip_path", sa.String(512), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_exports_project_id", "exports", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_exports_project_id", table_name="exports")
    op.drop_table("exports")
    sa.Enum(name="export_status").drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_photos_project_id", table_name="photos")
    op.drop_table("photos")
    op.drop_table("projects")
