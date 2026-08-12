from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.schemas import JobOfferCreate
from app.services.job_offers import (
    DuplicateJobOfferError,
    create_job_offer,
)


@dataclass(frozen=True)
class ImportResult:
    found: int
    added: int
    duplicates: int
    errors: int


def import_job_offers(
    db: Session,
    offers: Iterable[JobOfferCreate],
) -> ImportResult:
    found = 0
    added = 0
    duplicates = 0
    errors = 0

    for offer in offers:
        found += 1

        try:
            create_job_offer(
                db=db,
                data=offer,
            )
        except DuplicateJobOfferError:
            duplicates += 1
        except Exception:
            db.rollback()
            errors += 1

    return ImportResult(
        found=found,
        added=added + found - duplicates - errors,
        duplicates=duplicates,
        errors=errors,
    )