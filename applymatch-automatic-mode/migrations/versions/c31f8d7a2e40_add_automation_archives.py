"""Add automatic application policy archives.

Revision ID: c31f8d7a2e40
Revises: a29d4e8c613f
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c31f8d7a2e40"
down_revision: str | None = "a29d4e8c613f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "application_drafts",
        sa.Column("adapted_cv_snapshot", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "application_drafts",
        sa.Column("proposed_answers", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_table(
        "application_archives",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("company", sa.String(length=150), nullable=False),
        sa.Column("offer_title", sa.String(length=200), nullable=False),
        sa.Column("application_mode", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("provider_confirmation_id", sa.String(length=255), nullable=False),
        sa.Column("cv_snapshot", sa.Text(), nullable=False),
        sa.Column("cover_letter_snapshot", sa.Text(), nullable=False),
        sa.Column("short_message_snapshot", sa.Text(), nullable=False),
        sa.Column("proposed_answers_snapshot", sa.JSON(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["application_drafts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id"),
        sa.UniqueConstraint("provider_confirmation_id"),
    )
    op.create_index("ix_application_archives_draft_id", "application_archives", ["draft_id"])
    op.create_index("ix_application_archives_profile_id", "application_archives", ["profile_id"])
    op.create_index("ix_application_archives_offer_id", "application_archives", ["offer_id"])


def downgrade() -> None:
    op.drop_index("ix_application_archives_offer_id", table_name="application_archives")
    op.drop_index("ix_application_archives_profile_id", table_name="application_archives")
    op.drop_index("ix_application_archives_draft_id", table_name="application_archives")
    op.drop_table("application_archives")
    op.drop_column("application_drafts", "proposed_answers")
    op.drop_column("application_drafts", "adapted_cv_snapshot")
