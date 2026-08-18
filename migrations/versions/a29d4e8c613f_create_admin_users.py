"""Create admin users.

Revision ID: a29d4e8c613f
Revises: f18c3b7a920d
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a29d4e8c613f"
down_revision: str | None = "f18c3b7a920d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Les anciennes installations locales ont pu créer cette table via
    # Base.metadata.create_all avant l'ajout de la migration Alembic.
    if "admin_users" in sa.inspect(op.get_bind()).get_table_names():
        return

    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_users_email"),
        "admin_users",
        ["email"],
        unique=True,
    )
    op.create_index(
        op.f("ix_admin_users_is_active"),
        "admin_users",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_admin_users_is_active"),
        table_name="admin_users",
    )
    op.drop_index(
        op.f("ix_admin_users_email"),
        table_name="admin_users",
    )
    op.drop_table("admin_users")
