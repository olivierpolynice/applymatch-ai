import httpx
import pytest

from app.services.collectors.adzuna import (
    AdzunaCollector,
)
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
    def handler(request: httpx.Request) -> httpx.Response:
        if "access_token" in str(request.url):
            return httpx.Response(
                200,
                json={"access_token": "token"},
            )

        return httpx.Response(
            200,
            json={
                "resultats": [
                    {
                        "intitule": (
                            "Alternance ingénieur cloud"
                        ),
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


def test_adzuna_collects_and_deduplicates() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "adzuna-1",
                        "title": "Alternance DevSecOps cloud",
                        "description": (
                            "Alternance en sécurité cloud "
                            "avec Docker et réseau."
                        ),
                        "company": {
                            "display_name": "Entreprise Adzuna"
                        },
                        "location": {
                            "display_name": "Paris"
                        },
                        "contract_type": "apprentissage",
                        "redirect_url": (
                            "https://example.com/adzuna/1"
                        ),
                        "created": "2026-08-16T08:00:00Z",
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
    )
    collector = AdzunaCollector(
        app_id="app-id",
        app_key="app-key",
        client=client,
    )

    offers = collector.collect()

    assert len(offers) == 1
    assert offers[0].source == "Adzuna"


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
        lambda: AdzunaCollector(),
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
        "ADZUNA_APP_ID",
        "ADZUNA_APP_KEY",
        "JOOBLE_API_KEY",
    ):
        monkeypatch.delenv(variable, raising=False)

    with pytest.raises(CollectorConfigurationError):
        collector_factory()
