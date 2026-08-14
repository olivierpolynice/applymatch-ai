"""Create collector runs history.

Revision ID: a4d8c2f76190
Revises: f74c9a6b318e
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a4d8c2f76190"
down_revision: str | None = "f74c9a6b318e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collector_runs",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "collector",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "trigger",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "found",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "added",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "duplicates",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "errors",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_collector_runs_collector"),
        "collector_runs",
        ["collector"],
        unique=False,
    )
    op.create_index(
        op.f("ix_collector_runs_trigger"),
        "collector_runs",
        ["trigger"],
        unique=False,
    )
    op.create_index(
        op.f("ix_collector_runs_status"),
        "collector_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_collector_runs_started_at"),
        "collector_runs",
        ["started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_collector_runs_started_at"),
        table_name="collector_runs",
    )
    op.drop_index(
        op.f("ix_collector_runs_status"),
        table_name="collector_runs",
    )
    op.drop_index(
        op.f("ix_collector_runs_trigger"),
        table_name="collector_runs",
    )
    op.drop_index(
        op.f("ix_collector_runs_collector"),
        table_name="collector_runs",
    )

    op.drop_table("collector_runs")