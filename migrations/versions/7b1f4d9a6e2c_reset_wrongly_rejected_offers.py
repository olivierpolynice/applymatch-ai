"""Reset job offers wrongly marked as rejected by the matching engine.

save_match_result() (app/services/match_results.py) used to set
offer.status = "rejected" as soon as the matching algorithm scored an
offer poorly for the active candidate profile (wrong location, no
targeted domain/skill, etc.). evaluate_priority_offer()
(app/services/priority_filter.py) then excludes any offer whose status
is "rejected" from the browsing list - so a perfectly valid,
fresh alternance/stage offer that simply didn't match well would
disappear from the app entirely instead of just being deprioritized
for automatic application.

This is now fixed at the source (offer.status is no longer touched by
matching - only MatchResult.decision is). This migration is a one-time
data fix for offers that were already wrongly marked "rejected" in the
database by the old behaviour, so they become visible again.

There is no user-facing "reject this offer" action anywhere in the
app - offer.status only ever became "rejected" through the buggy
matching code path above - so it is safe to reset every offer
currently at status "rejected" back to "new".

Revision ID: 7b1f4d9a6e2c
Revises: c7a1e5f28b04
Create Date: 2026-08-25
"""

from collections.abc import Sequence

from alembic import op


revision: str = "7b1f4d9a6e2c"
down_revision: str | None = "c7a1e5f28b04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE job_offers SET status = 'new' "
        "WHERE status = 'rejected'"
    )


def downgrade() -> None:
    # Correction de donnees a sens unique : on ne sait plus, apres
    # coup, quelles offres avaient ete a tort marquees "rejected" par
    # le bug de matching corrige ici.
    pass
