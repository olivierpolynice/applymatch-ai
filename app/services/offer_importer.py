from collections.abc import Iterable
from dataclasses import dataclass
import hashlib
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import JobOffer
from app.schemas import JobOfferCreate
from app.services.job_offers import (
    DuplicateJobOfferError,
    build_offer_fingerprint,
    create_job_offer,
    normalize_fingerprint_value,
)


@dataclass(frozen=True)
class ImportResult:
    found: int
    added: int
    duplicates: int
    errors: int
    added_offer_ids: tuple[int, ...] = ()


def normalize_identity_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )

    return " ".join(without_accents.casefold().split())


def legacy_offer_identity(
    *,
    title: str,
    company: str,
    location: str,
) -> tuple[str, str, str]:
    return (
        normalize_identity_part(title),
        normalize_identity_part(company),
        normalize_identity_part(location),
    )


def legacy_stored_fingerprint(
    *,
    title: str,
    company: str,
    location: str,
) -> str:
    source = "|".join(
        normalize_fingerprint_value(value)
        for value in (title, company, location)
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def offer_fingerprint(
    *,
    title: str,
    company: str,
    location: str,
    source: str = "",
    external_id: str | None = None,
    source_url: str | None = None,
) -> str:
    return build_offer_fingerprint(
        title=title,
        company=company,
        location=location,
        source=source,
        external_id=external_id,
        source_url=source_url,
    )


def import_job_offers(
    db: Session,
    offers: Iterable[JobOfferCreate],
) -> ImportResult:
    found = 0
    duplicates = 0
    errors = 0
    added_offer_ids: list[int] = []
    known_fingerprints = set(
        db.scalars(select(JobOffer.fingerprint))
    )
    known_legacy_identities = {
        legacy_offer_identity(
            title=stored_offer.title,
            company=stored_offer.company,
            location=stored_offer.location,
        )
        for stored_offer in db.scalars(select(JobOffer))
        if stored_offer.fingerprint
        == legacy_stored_fingerprint(
            title=stored_offer.title,
            company=stored_offer.company,
            location=stored_offer.location,
        )
    }

    for offer in offers:
        found += 1
        fingerprint = offer_fingerprint(
            title=offer.title,
            company=offer.company,
            location=offer.location,
            source=offer.source,
            external_id=offer.external_id,
            source_url=(
                str(offer.source_url)
                if offer.source_url is not None
                else None
            ),
        )
        legacy_identity = legacy_offer_identity(
            title=offer.title,
            company=offer.company,
            location=offer.location,
        )

        if (
            fingerprint in known_fingerprints
            or legacy_identity in known_legacy_identities
        ):
            duplicates += 1
            continue

        try:
            created_offer = create_job_offer(
                db=db,
                data=offer,
            )
        except DuplicateJobOfferError:
            duplicates += 1
        except Exception:
            db.rollback()
            errors += 1
        else:
            known_fingerprints.add(fingerprint)
            added_offer_ids.append(
                created_offer.id,
            )

    return ImportResult(
        found=found,
        added=len(added_offer_ids),
        duplicates=duplicates,
        errors=errors,
        added_offer_ids=tuple(
            added_offer_ids,
        ),
    )
