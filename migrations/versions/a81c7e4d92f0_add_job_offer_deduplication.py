"""Add job offer deduplication.

Revision ID: a81c7e4d92f0
Revises: 6c445fd809a5
"""

import hashlib
import re
import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a81c7e4d92f0"
down_revision: str | None = "6c445fd809a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def normalize_fingerprint_value(value: str) -> str:
    normalized = unicodedata.normalize(
        "NFKC",
        value,
    )
    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip().casefold()


def build_fingerprint(
    title: str,
    company: str,
    location: str,
) -> str:
    source = "|".join(
        [
            normalize_fingerprint_value(title),
            normalize_fingerprint_value(company),
            normalize_fingerprint_value(location),
        ]
    )

    return hashlib.sha256(
        source.encode("utf-8"),
    ).hexdigest()


def upgrade() -> None:
    with op.batch_alter_table(
        "job_offers",
    ) as batch_op:
        batch_op.alter_column(
            "source_url",
            existing_type=sa.String(length=1000),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column(
                "fingerprint",
                sa.String(length=64),
                nullable=True,
            )
        )

    connection = op.get_bind()

    existing_offers = connection.execute(
        sa.text(
            """
            SELECT id, title, company, location
            FROM job_offers
            """
        )
    ).mappings()

    fingerprints: set[str] = set()

    for offer in existing_offers:
        fingerprint = build_fingerprint(
            title=offer["title"],
            company=offer["company"],
            location=offer["location"],
        )

        if fingerprint in fingerprints:
            raise RuntimeError(
                "Existing duplicate job offers must be "
                "resolved before this migration"
            )

        fingerprints.add(fingerprint)

        connection.execute(
            sa.text(
                """
                UPDATE job_offers
                SET fingerprint = :fingerprint
                WHERE id = :offer_id
                """
            ),
            {
                "fingerprint": fingerprint,
                "offer_id": offer["id"],
            },
        )

    with op.batch_alter_table(
        "job_offers",
    ) as batch_op:
        batch_op.alter_column(
            "fingerprint",
            existing_type=sa.String(length=64),
            nullable=False,
        )

    op.create_index(
        "ix_job_offers_fingerprint",
        "job_offers",
        ["fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_offers_fingerprint",
        table_name="job_offers",
    )

    with op.batch_alter_table(
        "job_offers",
    ) as batch_op:
        batch_op.drop_column("fingerprint")
        batch_op.alter_column(
            "source_url",
            existing_type=sa.String(length=1000),
            nullable=False,
        )