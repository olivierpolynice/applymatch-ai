from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.models import JobOffer
from app.schemas import JobOfferCreate
from app.services.priority_filter import (
    evaluate_priority_offer,
    extract_experience_range,
    parse_platform_datetime,
)


NOW = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)


def offer(
    *,
    title: str = "Ingénieur cloud junior",
    contract_type: str = "Alternance",
    published_at: datetime | None = NOW - timedelta(hours=2),
    description: str = "Poste junior avec une expérience de 0 à 2 ans.",
    experience_min: int | None = None,
    experience_max: int | None = None,
) -> JobOffer:
    return JobOffer(
        title=title,
        company="Entreprise Test",
        location="Paris",
        contract_type=contract_type,
        description=description,
        source="test",
        source_url=None,
        fingerprint="a" * 64,
        status="new",
        published_at=published_at,
        experience_min=experience_min,
        experience_max=experience_max,
    )


@pytest.mark.parametrize(
    "contract_type",
    [
        "Alternance",
        "Apprentissage",
        "Contrat de professionnalisation",
        "Stage",
    ],
)
def test_allowed_contracts_are_eligible(contract_type: str) -> None:
    result = evaluate_priority_offer(
        offer(contract_type=contract_type),
        now=NOW,
    )

    assert result.eligible is True
    assert result.reasons == ()


@pytest.mark.parametrize(
    "contract_type",
    ["CDI", "CDD de 12 mois", "Intérim", "Freelance"],
)
def test_forbidden_contracts_are_rejected(contract_type: str) -> None:
    result = evaluate_priority_offer(
        offer(contract_type=contract_type),
        now=NOW,
    )

    assert result.eligible is False
    assert "contrat_interdit" in result.reasons


def test_offer_older_than_24_hours_is_rejected() -> None:
    result = evaluate_priority_offer(
        offer(published_at=NOW - timedelta(hours=24, seconds=1)),
        now=NOW,
    )

    assert result.eligible is False
    assert "offre_plus_de_24_heures" in result.reasons


def test_offer_exactly_24_hours_old_is_allowed() -> None:
    result = evaluate_priority_offer(
        offer(published_at=NOW - timedelta(hours=24)),
        now=NOW,
    )

    assert result.eligible is True


def test_missing_publication_date_is_rejected() -> None:
    result = evaluate_priority_offer(
        offer(published_at=None),
        now=NOW,
    )

    assert result.eligible is False
    assert "date_publication_inconnue" in result.reasons


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Débutant accepté", (0, 2)),
        ("Profil junior", (0, 2)),
        ("Expérience de 0 à 2 ans", (0, 2)),
        ("2 ans d'expérience", (2, 2)),
        ("Expérience minimum 3 ans", (3, 3)),
    ],
)
def test_experience_extraction(
    text: str,
    expected: tuple[int, int],
) -> None:
    assert extract_experience_range(text) == expected


def test_more_than_two_years_is_rejected() -> None:
    result = evaluate_priority_offer(
        offer(
            description="Expérience minimum 3 ans exigée.",
        ),
        now=NOW,
    )

    assert result.eligible is False
    assert "experience_superieure_a_2_ans" in result.reasons


def test_unknown_experience_is_not_rejected() -> None:
    # Le contrat est deja alternance/stage (voir offer()), ce qui
    # implique par nature un profil debutant : une offre qui ne
    # precise pas explicitement le nombre d'annees d'experience ne
    # doit donc pas etre ecartee pour autant.
    result = evaluate_priority_offer(
        offer(
            title="Ingénieur cloud",
            description="Participation aux opérations de cybersécurité.",
        ),
        now=NOW,
    )

    assert result.eligible is True
    assert result.experience_min is None
    assert result.experience_max is None


@pytest.mark.parametrize(
    "raw_date",
    [
        "2026-08-21T08:30:00Z",
        "21/08/2026 10:30",
        "Fri, 21 Aug 2026 10:30:00 +0200",
    ],
)
def test_platform_dates_are_converted_to_utc(raw_date: str) -> None:
    parsed = parse_platform_datetime(raw_date)

    assert parsed is not None
    assert parsed.tzinfo == timezone.utc


def test_api_dates_are_normalized_to_utc() -> None:
    value = JobOfferCreate.model_validate(
        api_offer(
            suffix="utc",
            published_at=datetime.fromisoformat(
                "2026-08-21T10:00:00+02:00"
            ),
        )
    )

    assert value.published_at == datetime(
        2026,
        8,
        21,
        8,
        0,
        tzinfo=timezone.utc,
    )


def api_offer(
    *,
    suffix: str,
    published_at: datetime,
    contract_type: str = "Alternance",
    experience_min: int | None = 0,
    experience_max: int | None = 2,
) -> dict[str, object]:
    return {
        "title": f"Offre cloud {suffix}",
        "company": f"Entreprise {suffix}",
        "location": "Paris",
        "contract_type": contract_type,
        "description": (
            "Cette offre concerne les réseaux, le cloud et la cybersécurité."
        ),
        "source": "test_phase_2",
        "external_id": suffix,
        "source_url": f"https://example.com/jobs/{suffix}",
        "published_at": published_at.isoformat(),
        "experience_min": experience_min,
        "experience_max": experience_max,
    }


def test_priority_endpoint_only_returns_eligible_offers(
    authenticated_client: TestClient,
) -> None:
    current_time = datetime.now(timezone.utc)
    payloads = [
        api_offer(
            suffix="recent-alternance",
            published_at=current_time - timedelta(hours=2),
        ),
        api_offer(
            suffix="recent-stage",
            published_at=current_time - timedelta(hours=4),
            contract_type="Stage",
        ),
        api_offer(
            suffix="old",
            published_at=current_time - timedelta(hours=25),
        ),
        api_offer(
            suffix="cdi",
            published_at=current_time - timedelta(hours=1),
            contract_type="CDI",
        ),
        api_offer(
            suffix="too-experienced",
            published_at=current_time - timedelta(hours=1),
            experience_min=3,
            experience_max=5,
        ),
    ]

    for payload in payloads:
        response = authenticated_client.post(
            "/job-offers",
            json=payload,
        )
        assert response.status_code == 201

    response = authenticated_client.get(
        "/job-offers",
        params={"priority_only": True},
    )

    assert response.status_code == 200
    returned_ids = {item["external_id"] for item in response.json()}
    assert returned_ids == {"recent-alternance", "recent-stage"}
