"""Add matching algorithm v2 fields.

Revision ID: e82a7c4f913b
Revises: c31f8d7a2e40
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e82a7c4f913b"
down_revision: str | None = "c31f8d7a2e40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "match_results",
        sa.Column("experience_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "match_results",
        sa.Column("freshness_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "match_results",
        sa.Column("experience_match", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "match_results",
        sa.Column("eligibility_reasons", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("match_results", "eligibility_reasons")
    op.drop_column("match_results", "experience_match")
    op.drop_column("match_results", "freshness_score")
    op.drop_column("match_results", "experience_score")
