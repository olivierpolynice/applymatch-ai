import httpx
import pytest

from app.services.collectors.france_travail import (
    FranceTravailCollector,
)
from app.services.collectors.jooble import (
    JoobleCollector,
)
from app.services.collectors.la_bonne_alternance import (
    CollectorConfigurationError,
)


def test_france_travail_collects_relevant_offer() -> None:
    requested_departments: set[str] = set()

    def handler(request: httpx.Request) -> httpx.Response:
        if "access_token" in str(request.url):
            return httpx.Response(
                200,
                json={"access_token": "token"},
            )

        requested_departments.add(
            request.url.params["departement"]
        )
        return httpx.Response(
            200,
            json={
                "resultats": [
                    {
                        "intitule": (
                            "Alternance ingénieur cloud"
                        ),
                        "id": "ft-1",
                        "description": (
                            "Administration cloud, réseau et "
                            "sécurité informatique."
                        ),
                        "entreprise": {"nom": "Entreprise FT"},
                        "lieuTravail": {"libelle": "Paris 75"},
                        "typeContratLibelle": "Apprentissage",
                        "origineOffre": {
                            "urlOrigine": (
                                "https://example.com/ft/1"
                            )
                        },
                        "dateCreation": (
                            "2026-08-16T08:00:00Z"
                        ),
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
    )
    collector = FranceTravailCollector(
        client_id="client-id",
        client_secret="client-secret",
        client=client,
    )

    offers = collector.collect()

    assert len(offers) == 1
    assert offers[0].company == "Entreprise FT"
    assert offers[0].source == "France Travail"
    assert offers[0].external_id == "ft-1"
    assert offers[0].application_channel == "official_api"
    assert requested_departments == {
        "75", "77", "78", "91", "92", "93", "94", "95"
    }


def test_jooble_collects_and_deduplicates() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": "jooble-1",
                        "title": "Alternance cybersécurité",
                        "snippet": (
                            "Sécurité des systèmes, réseau "
                            "et environnement cloud."
                        ),
                        "company": "Entreprise Jooble",
                        "location": "Île-de-France",
                        "type": "Apprentissage",
                        "link": "https://example.com/jooble/1",
                        "updated": "2026-08-16T08:00:00Z",
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
    )
    collector = JoobleCollector(
        api_key="api-key",
        client=client,
    )

    offers = collector.collect()

    assert len(offers) == 1
    assert offers[0].source == "Jooble"


@pytest.mark.parametrize(
    "collector_factory",
    [
        lambda: FranceTravailCollector(),
        lambda: JoobleCollector(),
    ],
)
def test_external_collector_requires_credentials(
    collector_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in (
        "FRANCE_TRAVAIL_CLIENT_ID",
        "FRANCE_TRAVAIL_CLIENT_SECRET",
        "JOOBLE_API_KEY",
    ):
        monkeypatch.delenv(variable, raising=False)

    with pytest.raises(CollectorConfigurationError):
        collector_factory()
