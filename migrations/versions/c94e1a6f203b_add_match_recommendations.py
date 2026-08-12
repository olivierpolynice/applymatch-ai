"""Add match recommendations.

Revision ID: c94e1a6f203b
Revises: b73f2d8c410e
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c94e1a6f203b"
down_revision: str | None = "b73f2d8c410e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("match_results") as batch_op:
        batch_op.add_column(
            sa.Column(
                "decision",
                sa.String(length=30),
                nullable=False,
                server_default="consider",
            )
        )
        batch_op.add_column(
            sa.Column(
                "application_priority",
                sa.String(length=20),
                nullable=False,
                server_default="medium",
            )
        )
        batch_op.add_column(
            sa.Column(
                "actions",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("match_results") as batch_op:
        batch_op.drop_column("actions")
        batch_op.drop_column("application_priority")
        batch_op.drop_column("decision")