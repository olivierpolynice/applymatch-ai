"""Add portfolio_url to candidate_profiles.

Revision ID: c7a1e5f28b04
Revises: b4f6e0a913dc
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c7a1e5f28b04"
down_revision: str | None = "b4f6e0a913dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "portfolio_url",
            sa.String(length=300),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("candidate_profiles", "portfolio_url")