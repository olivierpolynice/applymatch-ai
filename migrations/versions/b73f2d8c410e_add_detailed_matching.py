"""Add detailed matching fields.

Revision ID: b73f2d8c410e
Revises: a81c7e4d92f0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b73f2d8c410e"
down_revision: str | None = "a81c7e4d92f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("match_results") as batch_op:
        batch_op.add_column(
            sa.Column(
                "confidence",
                sa.String(length=20),
                nullable=False,
                server_default="faible",
            )
        )
        batch_op.add_column(
            sa.Column(
                "skills_to_strengthen",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )
        batch_op.add_column(
            sa.Column(
                "education_score",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "education_match",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("match_results") as batch_op:
        batch_op.drop_column("education_match")
        batch_op.drop_column("education_score")
        batch_op.drop_column("skills_to_strengthen")
        batch_op.drop_column("confidence")