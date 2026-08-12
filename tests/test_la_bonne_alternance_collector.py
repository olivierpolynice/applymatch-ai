import httpx
import pytest

from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
    ILE_DE_FRANCE_DEPARTMENTS,
    LBA_SEARCH_URL,
    LaBonneAlternanceCollector,
    is_relevant_offer,
    transform_offer,
)


RAW_OFFER = {
    "identifier": {
        "partner_job_id": "offer-123",
        "id": "lba-123",
        "partner_label": "France Travail",
    },
    "workplace": {
        "name": "CyberCloud France",
        "brand": None,
        "legal_name": "CyberCloud France SAS",
        "location": {
            "address": "10 avenue de Paris 75001 Paris",
        },
    },
    "apply": {
        "url": "https://example.com/offres/offer-123",
        "phone": None,
    },
    "contract": {
        "type": [
            "Apprentissage",
        ],
        "start": "2026-09-01T00:00:00Z",
        "duration": 24,
        "remote": "hybrid",
    },
    "offer": {
        "title": "Alternance Ingénieur cybersécurité cloud",
        "description": (
            "Vous participerez à la sécurisation des infrastructures "
            "cloud et à la supervision des événements de sécurité."
        ),
        "desired_skills": [
            "Cloud",
            "SIEM",
            "Python",
        ],
        "to_be_acquired_skills": [
            "DevSecOps",
        ],
        "publication": {
            "creation": "2026-08-12T10:00:00Z",
            "expiration": "2026-10-12T10:00:00Z",
        },
        "rome_codes": [
            "M1802",
        ],
        "status": "Active",
    },
}


IRRELEVANT_OFFER = {
    **RAW_OFFER,
    "offer": {
        **RAW_OFFER["offer"],
        "title": "Alternance assistant comptable",
        "description": (
            "Vous participerez à la saisie des factures et au suivi "
            "administratif des dossiers clients de l’entreprise."
        ),
        "desired_skills": [
            "Comptabilité",
        ],
        "to_be_acquired_skills": [],
    },
}


def test_missing_api_key_returns_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "LBA_API_KEY",
        raising=False,
    )

    with pytest.raises(
        CollectorConfigurationError,
        match="LBA_API_KEY is not configured",
    ):
        LaBonneAlternanceCollector()


def test_transform_offer() -> None:
    offer = transform_offer(RAW_OFFER)

    assert offer.title == (
        "Alternance Ingénieur cybersécurité cloud"
    )
    assert offer.company == "CyberCloud France"
    assert offer.location == (
        "10 avenue de Paris 75001 Paris"
    )
    assert offer.contract_type == "Apprentissage"
    assert offer.source == (
        "La Bonne Alternance - France Travail"
    )
    assert str(offer.source_url) == (
        "https://example.com/offres/offer-123"
    )
    assert offer.published_at is not None
    assert offer.published_at.year == 2026


def test_relevant_offer_is_kept() -> None:
    assert is_relevant_offer(RAW_OFFER) is True


def test_irrelevant_offer_is_rejected() -> None:
    assert is_relevant_offer(IRRELEVANT_OFFER) is False


def test_collector_fetches_and_filters_offers() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert str(request.url).startswith(
            LBA_SEARCH_URL
        )
        assert request.headers["Authorization"] == (
            "Bearer test-api-key"
        )
        assert request.url.params[
            "target_diploma_level"
        ] == "7"

        departments = request.url.params.get_list(
            "departements"
        )

        assert departments == ILE_DE_FRANCE_DEPARTMENTS

        return httpx.Response(
            status_code=200,
            json={
                "jobs": [
                    RAW_OFFER,
                    IRRELEVANT_OFFER,
                ],
                "recruiters": [],
                "warnings": [],
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
    )
    collector = LaBonneAlternanceCollector(
        api_key="test-api-key",
        client=client,
    )

    try:
        offers = collector.collect()
    finally:
        client.close()

    assert len(offers) == 1
    assert offers[0].company == "CyberCloud France"


def test_api_error_is_converted_to_collector_error() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=401,
            json={
                "message": "Unauthorized",
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
    )
    collector = LaBonneAlternanceCollector(
        api_key="invalid-api-key",
        client=client,
    )

    try:
        with pytest.raises(
            CollectorAPIError,
            match=(
                "La Bonne Alternance API request failed"
            ),
        ):
            collector.fetch_raw_offers()
    finally:
        client.close()


def test_invalid_api_response_returns_error() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "jobs": None,
                "recruiters": [],
                "warnings": [],
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
    )
    collector = LaBonneAlternanceCollector(
        api_key="test-api-key",
        client=client,
    )

    try:
        with pytest.raises(
            CollectorAPIError,
            match=(
                "Invalid La Bonne Alternance response"
            ),
        ):
            collector.fetch_raw_offers()
    finally:
        client.close()