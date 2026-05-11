"""add cpl look pipeline setting

Revision ID: 0008_cpl_look
Revises: 0007_batch_versions
Create Date: 2026-05-11 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_cpl_look"
down_revision: Union[str, None] = "0007_batch_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cpl_strength = postgresql.ENUM("none", "low", "medium", "high", name="cpl_strength")
    cpl_strength.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "processing_jobs",
        sa.Column(
            "cpl_strength",
            cpl_strength,
            nullable=False,
            server_default="none",
        ),
    )
    op.alter_column("processing_jobs", "cpl_strength", server_default=None)


def downgrade() -> None:
    op.drop_column("processing_jobs", "cpl_strength")
    postgresql.ENUM(name="cpl_strength").drop(op.get_bind(), checkfirst=True)
