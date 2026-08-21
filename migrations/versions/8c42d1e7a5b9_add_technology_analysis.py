"""Add structured technology analysis to match results.

Revision ID: 8c42d1e7a5b9
Revises: f3a91d6c2e74
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "8c42d1e7a5b9"
down_revision: str | None = "f3a91d6c2e74"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "match_results",
        sa.Column(
            "known_technologies",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "match_results",
        sa.Column(
            "unknown_technologies",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "match_results",
        sa.Column(
            "required_technologies",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "match_results",
        sa.Column(
            "preferred_technologies",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("match_results", "preferred_technologies")
    op.drop_column("match_results", "required_technologies")
    op.drop_column("match_results", "unknown_technologies")
    op.drop_column("match_results", "known_technologies")
