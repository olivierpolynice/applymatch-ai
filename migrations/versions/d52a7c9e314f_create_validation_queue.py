"""Create validation queue.

Revision ID: d52a7c9e314f
Revises: c94e1a6f203b
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "d52a7c9e314f"
down_revision: str | None = "c94e1a6f203b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "validation_queue_items",
        sa.Column(
            "id",
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
            "match_result_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "reviewer_comment",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["job_offers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["match_result_id"],
            ["match_results.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_result_id",
            name=(
                "uq_validation_queue_items_match_result_id"
            ),
        ),
        sa.UniqueConstraint(
            "profile_id",
            "offer_id",
            name=(
                "uq_validation_queue_items_profile_offer"
            ),
        ),
    )

    op.create_index(
        "ix_validation_queue_items_profile_id",
        "validation_queue_items",
        ["profile_id"],
    )
    op.create_index(
        "ix_validation_queue_items_offer_id",
        "validation_queue_items",
        ["offer_id"],
    )
    op.create_index(
        "ix_validation_queue_items_match_result_id",
        "validation_queue_items",
        ["match_result_id"],
        unique=True,
    )
    op.create_index(
        "ix_validation_queue_items_status",
        "validation_queue_items",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_validation_queue_items_status",
        table_name="validation_queue_items",
    )
    op.drop_index(
        "ix_validation_queue_items_match_result_id",
        table_name="validation_queue_items",
    )
    op.drop_index(
        "ix_validation_queue_items_offer_id",
        table_name="validation_queue_items",
    )
    op.drop_index(
        "ix_validation_queue_items_profile_id",
        table_name="validation_queue_items",
    )
    op.drop_table("validation_queue_items")