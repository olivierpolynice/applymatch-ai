import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CollectorRun
from app.schemas import JobOfferCreate
from app.services import collector_runs


OPTIONAL_COLLECTOR_VARIABLES = (
    "GREENHOUSE_BOARDS",
    "LEVER_SITES",
    "SMARTRECRUITERS_COMPANIES",
    "EMPLOI_TERRITORIAL_RSS_URL",
)


@pytest.mark.parametrize(
    "path",
    [
        "/collectors/la-bonne-alternance/run",
        "/collectors/france-travail/run",
        "/collectors/jooble/run",
        "/collectors/choisir-service-public/run",
        "/collectors/emploi-territorial/run",
        "/collectors/greenhouse/run",
        "/collectors/lever/run",
        "/collectors/smartrecruiters/run",
        "/collectors/run-all",
    ],
)
def test_collector_run_requires_authentication(
    client: TestClient,
    path: str,
) -> None:
    response = client.post(path)

    assert response.status_code == 401


def build_offer(
    source: str,
    identifier: str,
) -> JobOfferCreate:
    return JobOfferCreate(
        title=f"Alternance cloud {identifier}",
        company=f"Entreprise {identifier}",
        location="Paris",
        contract_type="Apprentissage",
        description=(
            "Alternance en cybersécurité, réseau, "
            "cloud et automatisation DevSecOps."
        ),
        source=source,
        source_url=(
            f"https://example.com/{identifier}"
        ),
        published_at=None,
    )


def disable_optional_collectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in OPTIONAL_COLLECTOR_VARIABLES:
        monkeypatch.delenv(
            variable,
            raising=False,
        )


def mock_public_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        collector_runs,
        "collect_choisir_service_public_offers",
        lambda: [],
    )


def test_run_all_configured_collectors(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = {
        "LBA_API_KEY": "lba-key",
        "FRANCE_TRAVAIL_CLIENT_ID": "ft-id",
        "FRANCE_TRAVAIL_CLIENT_SECRET": (
            "ft-secret"
        ),
        "JOOBLE_API_KEY": "jooble-key",
    }

    disable_optional_collectors(monkeypatch)
    mock_public_collector(monkeypatch)

    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    monkeypatch.setattr(
        collector_runs,
        "collect_lba_offers",
        lambda: [
            build_offer(
                "La Bonne Alternance",
                "lba",
            )
        ],
    )
    monkeypatch.setattr(
        collector_runs,
        "collect_france_travail_offers",
        lambda: [
            build_offer(
                "France Travail",
                "ft",
            )
        ],
    )
    monkeypatch.setattr(
        collector_runs,
        "collect_jooble_offers",
        lambda: [
            build_offer(
                "Jooble",
                "jooble",
            )
        ],
    )

    response = authenticated_client.post(
        "/collectors/run-all",
    )

    assert response.status_code == 200
    assert response.json() == {
        "found": 3,
        "added": 3,
        "duplicates": 0,
        "errors": 0,
    }

    run_count = db_session.scalar(
        select(func.count()).select_from(
            CollectorRun
        )
    )

    # Trois collecteurs configurés, plus le collecteur
    # public Choisir le Service Public.
    assert run_count == 4


def test_run_all_skips_unconfigured_collectors(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in (
        "LBA_API_KEY",
        "FRANCE_TRAVAIL_CLIENT_ID",
        "FRANCE_TRAVAIL_CLIENT_SECRET",
        "JOOBLE_API_KEY",
        *OPTIONAL_COLLECTOR_VARIABLES,
    ):
        monkeypatch.delenv(
            variable,
            raising=False,
        )

    mock_public_collector(monkeypatch)

    response = authenticated_client.post(
        "/collectors/run-all",
    )

    assert response.status_code == 200
    assert response.json() == {
        "found": 0,
        "added": 0,
        "duplicates": 0,
        "errors": 0,
    }

    run_count = db_session.scalar(
        select(func.count()).select_from(
            CollectorRun
        )
    )

    # Choisir le Service Public ne nécessite aucune clé
    # et doit donc toujours être exécuté.
    assert run_count == 1