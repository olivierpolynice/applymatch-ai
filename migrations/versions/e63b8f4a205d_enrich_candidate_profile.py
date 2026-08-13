"""Enrich candidate profile.

Revision ID: e63b8f4a205d
Revises: d52a7c9e314f
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e63b8f4a205d"
down_revision: str | None = "d52a7c9e314f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table(
        "candidate_profiles",
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "professional_summary",
                sa.Text(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "experience_highlights",
                sa.Text(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "project_highlights",
                sa.Text(),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "candidate_profiles",
    ) as batch_op:
        batch_op.drop_column("project_highlights")
        batch_op.drop_column("experience_highlights")
        batch_op.drop_column("professional_summary")