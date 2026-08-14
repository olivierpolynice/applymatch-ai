"""Create application drafts.

Revision ID: f74c9a6b318e
Revises: e63b8f4a205d
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f74c9a6b318e"
down_revision: str | None = "e63b8f4a205d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "application_drafts",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "validation_queue_item_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "profile_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "offer_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "cover_letter",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "short_message",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "cv_adaptation_tips",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["validation_queue_item_id"],
            ["validation_queue_items.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["job_offers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "validation_queue_item_id",
            name=(
                "uq_application_drafts_"
                "validation_queue_item"
            ),
        ),
    )

    op.create_index(
        "ix_application_drafts_validation_queue_item_id",
        "application_drafts",
        ["validation_queue_item_id"],
    )
    op.create_index(
        "ix_application_drafts_profile_id",
        "application_drafts",
        ["profile_id"],
    )
    op.create_index(
        "ix_application_drafts_offer_id",
        "application_drafts",
        ["offer_id"],
    )
    op.create_index(
        "ix_application_drafts_status",
        "application_drafts",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_drafts_status",
        table_name="application_drafts",
    )
    op.drop_index(
        "ix_application_drafts_offer_id",
        table_name="application_drafts",
    )
    op.drop_index(
        "ix_application_drafts_profile_id",
        table_name="application_drafts",
    )
    op.drop_index(
        (
            "ix_application_drafts_"
            "validation_queue_item_id"
        ),
        table_name="application_drafts",
    )

    op.drop_table("application_drafts")