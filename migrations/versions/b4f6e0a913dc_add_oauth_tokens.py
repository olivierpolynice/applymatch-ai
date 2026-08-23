"""Add oauth_tokens table for persistent Gmail token storage.

Revision ID: b4f6e0a913dc
Revises: ea70c9f281b4
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b4f6e0a913dc"
down_revision: str | None = "ea70c9f281b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oauth_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("token_json", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.UniqueConstraint("provider"),
    )
    op.create_index(
        "ix_oauth_tokens_provider",
        "oauth_tokens",
        ["provider"],
    )


def downgrade() -> None:
    op.drop_index("ix_oauth_tokens_provider", table_name="oauth_tokens")
    op.drop_table("oauth_tokens")
