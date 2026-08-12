from fastapi.testclient import TestClient

from app.api.routes import collectors
from app.schemas import JobOfferCreate
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
)


def build_collected_offer() -> JobOfferCreate:
    return JobOfferCreate(
        title="Alternance Ingénieur IA et Cloud",
        company="Entreprise Innovation",
        location="Paris",
        contract_type="Apprentissage",
        description=(
            "Participation au développement de solutions "
            "d'intelligence artificielle sur une plateforme cloud."
        ),
        source="La Bonne Alternance",
        source_url="https://example.com/offers/ai-cloud",
        published_at=None,
    )


def test_run_collector_imports_offers(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        collectors,
        "collect_lba_offers",
        lambda: [build_collected_offer()],
    )

    response = client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert response.status_code == 200
    assert response.json() == {
        "found": 1,
        "added": 1,
        "duplicates": 0,
        "errors": 0,
    }

    offers_response = client.get("/job-offers")

    assert offers_response.status_code == 200
    assert len(offers_response.json()) == 1
    assert offers_response.json()[0]["company"] == (
        "Entreprise Innovation"
    )


def test_run_collector_reports_duplicates(
    client: TestClient,
    monkeypatch,
) -> None:
    offer = build_collected_offer()

    monkeypatch.setattr(
        collectors,
        "collect_lba_offers",
        lambda: [offer],
    )

    first_response = client.post(
        "/collectors/la-bonne-alternance/run"
    )
    second_response = client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert first_response.status_code == 200
    assert first_response.json()["added"] == 1

    assert second_response.status_code == 200
    assert second_response.json() == {
        "found": 1,
        "added": 0,
        "duplicates": 1,
        "errors": 0,
    }


def test_run_collector_without_api_key_returns_503(
    client: TestClient,
    monkeypatch,
) -> None:
    def raise_configuration_error():
        raise CollectorConfigurationError(
            "LBA_API_KEY is not configured"
        )

    monkeypatch.setattr(
        collectors,
        "collect_lba_offers",
        raise_configuration_error,
    )

    response = client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "La Bonne Alternance API key is not configured"
        )
    }


def test_run_collector_api_error_returns_502(
    client: TestClient,
    monkeypatch,
) -> None:
    def raise_api_error():
        raise CollectorAPIError(
            "La Bonne Alternance API request failed"
        )

    monkeypatch.setattr(
        collectors,
        "collect_lba_offers",
        raise_api_error,
    )

    response = client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "La Bonne Alternance API is unavailable"
    }