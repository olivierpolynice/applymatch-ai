"""Consolidate the job offer and application lifecycle.

Revision ID: f3a91d6c2e74
Revises: e82a7c4f913b
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f3a91d6c2e74"
down_revision: str | None = "e82a7c4f913b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_offers",
        sa.Column("external_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "job_offers",
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "job_offers",
        sa.Column("experience_min", sa.Integer(), nullable=True),
    )
    op.add_column(
        "job_offers",
        sa.Column("experience_max", sa.Integer(), nullable=True),
    )
    op.add_column(
        "job_offers",
        sa.Column(
            "application_channel",
            sa.String(length=40),
            nullable=True,
        ),
    )
    op.add_column(
        "job_offers",
        sa.Column(
            "application_status",
            sa.String(length=40),
            nullable=False,
            server_default="not_started",
        ),
    )
    op.add_column(
        "job_offers",
        sa.Column(
            "provider_confirmation_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_job_offers_expires_at",
        "job_offers",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_job_offers_application_status",
        "job_offers",
        ["application_status"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_job_offers_source_external_id",
        "job_offers",
        ["source", "external_id"],
    )
    op.create_unique_constraint(
        "uq_job_offers_provider_confirmation_id",
        "job_offers",
        ["provider_confirmation_id"],
    )

    op.create_check_constraint(
        "ck_job_offers_experience_min_non_negative",
        "job_offers",
        "experience_min IS NULL OR experience_min >= 0",
    )
    op.create_check_constraint(
        "ck_job_offers_experience_max_non_negative",
        "job_offers",
        "experience_max IS NULL OR experience_max >= 0",
    )
    op.create_check_constraint(
        "ck_job_offers_experience_range",
        "job_offers",
        "experience_min IS NULL OR experience_max IS NULL "
        "OR experience_min <= experience_max",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_job_offers_experience_range",
        "job_offers",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_offers_experience_max_non_negative",
        "job_offers",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_offers_experience_min_non_negative",
        "job_offers",
        type_="check",
    )

    op.drop_constraint(
        "uq_job_offers_provider_confirmation_id",
        "job_offers",
        type_="unique",
    )
    op.drop_constraint(
        "uq_job_offers_source_external_id",
        "job_offers",
        type_="unique",
    )
    op.drop_index(
        "ix_job_offers_application_status",
        table_name="job_offers",
    )
    op.drop_index(
        "ix_job_offers_expires_at",
        table_name="job_offers",
    )

    op.drop_column("job_offers", "provider_confirmation_id")
    op.drop_column("job_offers", "application_status")
    op.drop_column("job_offers", "application_channel")
    op.drop_column("job_offers", "experience_max")
    op.drop_column("job_offers", "experience_min")
    op.drop_column("job_offers", "expires_at")
    op.drop_column("job_offers", "external_id")
