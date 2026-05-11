"""add chroma clean strength

Revision ID: 0009_chroma_clean
Revises: 0008_cpl_look
Create Date: 2026-05-11 19:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_chroma_clean"
down_revision: str | None = "0008_cpl_look"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    chroma_clean_strength = postgresql.ENUM("none", "low", "medium", "high", name="chroma_clean_strength")
    chroma_clean_strength.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "processing_jobs",
        sa.Column(
            "chroma_clean_strength",
            chroma_clean_strength,
            nullable=False,
            server_default="none",
        ),
    )
    op.alter_column("processing_jobs", "chroma_clean_strength", server_default=None)


def downgrade() -> None:
    op.drop_column("processing_jobs", "chroma_clean_strength")
    postgresql.ENUM(name="chroma_clean_strength").drop(op.get_bind(), checkfirst=True)
