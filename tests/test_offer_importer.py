from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import JobOffer
from app.schemas import JobOfferCreate
from app.services.offer_importer import import_job_offers


def build_offer(
    *,
    title: str,
    company: str,
    source_url: str | None,
) -> JobOfferCreate:
    return JobOfferCreate(
        title=title,
        company=company,
        location="Paris",
        contract_type="Apprentissage",
        description=(
            "Cette offre concerne une alternance dans les domaines "
            "de la cybersécurité, du cloud et des réseaux."
        ),
        source="La Bonne Alternance",
        source_url=source_url,
        published_at=None,
    )


def test_import_job_offers_adds_new_offers(
    db_session: Session,
) -> None:
    offers = [
        build_offer(
            title="Alternance cybersécurité",
            company="Entreprise A",
            source_url="https://example.com/offers/1",
        ),
        build_offer(
            title="Alternance intelligence artificielle",
            company="Entreprise B",
            source_url="https://example.com/offers/2",
        ),
    ]

    result = import_job_offers(
        db=db_session,
        offers=offers,
    )

    stored_offers = list(
        db_session.scalars(
            select(JobOffer).order_by(JobOffer.id)
        )
    )

    assert result.found == 2
    assert result.added == 2
    assert result.duplicates == 0
    assert result.errors == 0
    assert len(stored_offers) == 2


def test_import_job_offers_ignores_duplicates(
    db_session: Session,
) -> None:
    offer = build_offer(
        title="Alternance DevSecOps",
        company="Entreprise Cyber",
        source_url="https://example.com/offers/devsecops",
    )

    first_result = import_job_offers(
        db=db_session,
        offers=[offer],
    )
    second_result = import_job_offers(
        db=db_session,
        offers=[offer],
    )

    stored_offers = list(
        db_session.scalars(
            select(JobOffer)
        )
    )

    assert first_result.added == 1
    assert second_result.found == 1
    assert second_result.added == 0
    assert second_result.duplicates == 1
    assert second_result.errors == 0
    assert len(stored_offers) == 1


def test_import_detects_duplicate_without_url(
    db_session: Session,
) -> None:
    first_offer = build_offer(
        title="Alternance Machine Learning",
        company="Entreprise IA",
        source_url=None,
    )
    duplicate_offer = build_offer(
        title="  ALTERNANCE MACHINE LEARNING  ",
        company="  ENTREPRISE IA ",
        source_url=None,
    )

    result = import_job_offers(
        db=db_session,
        offers=[
            first_offer,
            duplicate_offer,
        ],
    )

    assert result.found == 2
    assert result.added == 1
    assert result.duplicates == 1
    assert result.errors == 0