from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas import JobOfferCreate


def valid_offer_data() -> dict[str, object]:
    return {
        "title": "Alternance ingénieur cloud junior",
        "company": "Entreprise Test",
        "location": "Paris",
        "contract_type": "Alternance",
        "description": (
            "Participation aux projets cloud, réseau et cybersécurité "
            "avec accompagnement par une équipe expérimentée."
        ),
        "source": "france_travail",
        "external_id": "FT-2026-0001",
        "source_url": "https://example.com/jobs/FT-2026-0001",
        "published_at": "2026-08-21T00:00:00+02:00",
        "expires_at": "2026-09-21T00:00:00+02:00",
        "experience_min": 0,
        "experience_max": 2,
    }


def test_job_offer_lifecycle_fields_are_persisted(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/job-offers",
        json=valid_offer_data(),
    )

    assert response.status_code == 201
    offer = response.json()
    assert offer["external_id"] == "FT-2026-0001"
    assert offer["experience_min"] == 0
    assert offer["experience_max"] == 2
    assert offer["expires_at"] is not None
    assert offer["application_channel"] is None
    assert offer["application_status"] == "not_started"
    assert offer["provider_confirmation_id"] is None


def test_same_external_id_is_unique_per_source(
    authenticated_client: TestClient,
) -> None:
    first = valid_offer_data()
    second = valid_offer_data()
    second["title"] = "Stage administrateur réseaux"
    second["company"] = "Autre entreprise"
    second["source_url"] = "https://example.com/jobs/duplicate-external-id"

    first_response = authenticated_client.post(
        "/job-offers",
        json=first,
    )
    second_response = authenticated_client.post(
        "/job-offers",
        json=second,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "A job offer with this source and external ID already exists"
    )


@pytest.mark.parametrize(
    ("experience_min", "experience_max"),
    [
        (-1, 2),
        (0, -1),
        (3, 2),
    ],
)
def test_invalid_experience_range_is_rejected(
    experience_min: int,
    experience_max: int,
) -> None:
    data = valid_offer_data()
    data["experience_min"] = experience_min
    data["experience_max"] = experience_max

    with pytest.raises(ValidationError):
        JobOfferCreate.model_validate(data)


def test_naive_publication_date_is_rejected() -> None:
    data = valid_offer_data()
    data["published_at"] = datetime(2026, 8, 21, 8, 0)

    with pytest.raises(ValidationError):
        JobOfferCreate.model_validate(data)


def test_expiration_must_follow_publication() -> None:
    data = valid_offer_data()
    data["published_at"] = datetime(
        2026,
        8,
        21,
        8,
        0,
        tzinfo=timezone.utc,
    )
    data["expires_at"] = datetime(
        2026,
        8,
        20,
        8,
        0,
        tzinfo=timezone.utc,
    )

    with pytest.raises(ValidationError):
        JobOfferCreate.model_validate(data)


def test_manual_application_updates_lifecycle_fields(
    authenticated_client: TestClient,
) -> None:
    create_response = authenticated_client.post(
        "/job-offers",
        json=valid_offer_data(),
    )
    offer_id = create_response.json()["id"]

    response = authenticated_client.post(
        f"/job-offers/{offer_id}/mark-applied",
    )

    assert response.status_code == 200
    offer = response.json()
    assert offer["status"] == "applied"
    assert offer["application_channel"] == "manual"
    assert offer["application_status"] == "sent"
    assert offer["provider_confirmation_id"].startswith(
        f"manual-{offer_id}-"
    )
