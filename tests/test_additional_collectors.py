import httpx

from app.services.collectors.choisir_service_public import (
    collect_choisir_service_public_offers,
)
from app.services.collectors.emploi_territorial import (
    collect_emploi_territorial_offers,
)
from app.services.collectors.greenhouse import (
    collect_greenhouse_offers,
)
from app.services.collectors.lever import collect_lever_offers
from app.services.collectors.smartrecruiters import (
    collect_smartrecruiters_offers,
)


def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_csp_collector() -> None:
    csv_data = (
        "Organisme de rattachement;Référence;Métier;Nature de l'emploi;"
        "Intitulé du poste;Lieu d'affectation;Date de fin de publication "
        "par défaut;Date de première publication;Spécialisation;Employeur;"
        "Compétences attendues;Nature de contrat;Durée du contrat\n"
        "État;ABC-1;Sécurité;Apprentissage;Alternance cybersécurité;Paris;"
        "31/12/2099;01/08/2026;Cloud;Ministère;SIEM DevSecOps;Alternance;1 an\n"
    )
    offers = collect_choisir_service_public_offers(
        client(lambda _: httpx.Response(200, text=csv_data))
    )
    assert len(offers) == 1
    assert offers[0].company == "Ministère"
    assert len(offers[0].description) >= 20
    assert offers[0].published_at is not None
    assert offers[0].published_at.utcoffset() is not None


def test_emploi_territorial_collector(monkeypatch) -> None:
    monkeypatch.setenv("EMPLOI_TERRITORIAL_RSS_URL", "https://test/rss")
    xml = """<rss><channel><item><title>Alternance cloud</title>
    <description>Apprenti DevSecOps cybersécurité</description>
    <link>https://test/job</link></item></channel></rss>"""
    offers = collect_emploi_territorial_offers(
        client(lambda _: httpx.Response(200, text=xml))
    )
    assert len(offers) == 1


def test_greenhouse_collector(monkeypatch) -> None:
    monkeypatch.setenv("GREENHOUSE_BOARDS", "demo")
    payload = {"jobs": [{"title": "Alternance cloud", "content": "DevSecOps", "location": {"name": "Paris"}, "absolute_url": "https://test/job"}]}
    offers = collect_greenhouse_offers(
        client(lambda _: httpx.Response(200, json=payload))
    )
    assert len(offers) == 1


def test_lever_collector(monkeypatch) -> None:
    monkeypatch.setenv("LEVER_SITES", "demo")
    payload = [{"text": "Apprenti réseau", "descriptionPlain": "Alternance cybersécurité", "categories": {"location": "Paris", "commitment": "Apprentissage"}, "hostedUrl": "https://test/job"}]
    offers = collect_lever_offers(
        client(lambda _: httpx.Response(200, json=payload))
    )
    assert len(offers) == 1


def test_smartrecruiters_collector(monkeypatch) -> None:
    monkeypatch.setenv("SMARTRECRUITERS_COMPANIES", "demo")
    listing = {"content": [{"id": "1", "name": "Alternance DevSecOps", "company": {"name": "Demo"}, "location": {"city": "Paris", "country": "fr"}, "typeOfEmployment": {"label": "Apprentissage"}}]}
    detail = {"applyUrl": "https://test/job", "jobAd": {"sections": {"jobDescription": {"text": "Cybersécurité cloud"}}}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=detail if request.url.path.endswith("/1") else listing)

    offers = collect_smartrecruiters_offers(client(handler))
    assert len(offers) == 1
