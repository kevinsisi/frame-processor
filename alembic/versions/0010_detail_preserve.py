"""add detail preserve strength

Revision ID: 0010_detail_preserve
Revises: 0009_chroma_clean
Create Date: 2026-05-12 00:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_detail_preserve"
down_revision: str | None = "0009_chroma_clean"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    detail_preserve_strength = postgresql.ENUM("none", "low", "medium", "high", name="detail_preserve_strength")
    detail_preserve_strength.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "processing_jobs",
        sa.Column(
            "detail_preserve_strength",
            detail_preserve_strength,
            nullable=False,
            server_default="none",
        ),
    )
    op.alter_column("processing_jobs", "detail_preserve_strength", server_default=None)


def downgrade() -> None:
    op.drop_column("processing_jobs", "detail_preserve_strength")
    postgresql.ENUM(name="detail_preserve_strength").drop(op.get_bind(), checkfirst=True)
