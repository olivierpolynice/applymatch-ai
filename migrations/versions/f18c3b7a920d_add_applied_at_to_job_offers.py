"""Add application date to job offers.

Revision ID: f18c3b7a920d
Revises: b7e91a4d306c
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f18c3b7a920d"
down_revision: str | None = "b7e91a4d306c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_offers",
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_job_offers_applied_at"),
        "job_offers",
        ["applied_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_job_offers_applied_at"),
        table_name="job_offers",
    )

    op.drop_column(
        "job_offers",
        "applied_at",
    )
