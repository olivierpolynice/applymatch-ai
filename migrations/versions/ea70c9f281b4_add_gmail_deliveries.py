"""Add Gmail draft and delivery confirmations.

Revision ID: ea70c9f281b4
Revises: 8c42d1e7a5b9
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "ea70c9f281b4"
down_revision: str | None = "8c42d1e7a5b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gmail_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("gmail_draft_id", sa.String(length=255), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["draft_id"], ["application_drafts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id"),
        sa.UniqueConstraint("gmail_draft_id"),
        sa.UniqueConstraint("gmail_message_id"),
    )
    op.create_index(
        "ix_gmail_deliveries_draft_id", "gmail_deliveries", ["draft_id"]
    )
    op.create_index(
        "ix_gmail_deliveries_status", "gmail_deliveries", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_gmail_deliveries_status", table_name="gmail_deliveries")
    op.drop_index("ix_gmail_deliveries_draft_id", table_name="gmail_deliveries")
    op.drop_table("gmail_deliveries")
