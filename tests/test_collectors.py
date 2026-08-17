import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CollectorRun
from app.schemas import JobOfferCreate
from app.services import collector_runs
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
)


def build_collected_offer() -> JobOfferCreate:
    return JobOfferCreate(
        title="Alternance IngÃ©nieur IA et Cloud",
        company="Entreprise Innovation",
        location="Paris",
        contract_type="Apprentissage",
        description=(
            "Participation au dÃ©veloppement de solutions "
            "d'intelligence artificielle sur une "
            "plateforme cloud."
        ),
        source="La Bonne Alternance",
        source_url=(
            "https://example.com/offers/ai-cloud"
        ),
        published_at=None,
    )


def test_run_collector_imports_offers(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        collector_runs,
        "collect_lba_offers",
        lambda: [build_collected_offer()],
    )

    response = authenticated_client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert response.status_code == 200
    assert response.json() == {
        "found": 1,
        "added": 1,
        "duplicates": 0,
        "errors": 0,
    }

    offers_response = authenticated_client.get("/job-offers")

    assert offers_response.status_code == 200
    assert len(offers_response.json()) == 1
    assert offers_response.json()[0]["company"] == (
        "Entreprise Innovation"
    )

    stored_run = db_session.scalar(
        select(CollectorRun)
    )

    assert stored_run is not None
    assert stored_run.trigger == "manual"
    assert stored_run.status == "completed"
    assert stored_run.found == 1
    assert stored_run.added == 1
    assert stored_run.duplicates == 0
    assert stored_run.errors == 0
    assert stored_run.error_message is None
    assert stored_run.finished_at is not None


def test_run_collector_reports_duplicates(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offer = build_collected_offer()

    monkeypatch.setattr(
        collector_runs,
        "collect_lba_offers",
        lambda: [offer],
    )

    first_response = authenticated_client.post(
        "/collectors/la-bonne-alternance/run"
    )
    second_response = authenticated_client.post(
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

    stored_count = db_session.scalar(
        select(func.count()).select_from(
            CollectorRun
        )
    )

    assert stored_count == 2

    latest_run = db_session.scalar(
        select(CollectorRun)
        .order_by(CollectorRun.id.desc())
        .limit(1)
    )

    assert latest_run is not None
    assert latest_run.status == "completed"
    assert latest_run.found == 1
    assert latest_run.added == 0
    assert latest_run.duplicates == 1


def test_run_collector_without_api_key_returns_503(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_configuration_error():
        raise CollectorConfigurationError(
            "LBA_API_KEY is not configured"
        )

    monkeypatch.setattr(
        collector_runs,
        "collect_lba_offers",
        raise_configuration_error,
    )

    response = authenticated_client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "La Bonne Alternance API key "
            "is not configured"
        )
    }

    stored_run = db_session.scalar(
        select(CollectorRun)
    )

    assert stored_run is not None
    assert stored_run.status == "failed"
    assert stored_run.trigger == "manual"
    assert stored_run.errors == 1
    assert stored_run.error_message == (
        "LBA_API_KEY is not configured"
    )
    assert stored_run.finished_at is not None


def test_run_collector_api_error_returns_502(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_api_error():
        raise CollectorAPIError(
            "La Bonne Alternance API request failed"
        )

    monkeypatch.setattr(
        collector_runs,
        "collect_lba_offers",
        raise_api_error,
    )

    response = authenticated_client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": (
            "La Bonne Alternance API "
            "is unavailable"
        )
    }

    stored_run = db_session.scalar(
        select(CollectorRun)
    )

    assert stored_run is not None
    assert stored_run.status == "failed"
    assert stored_run.trigger == "manual"
    assert stored_run.errors == 1
    assert stored_run.error_message == (
        "La Bonne Alternance API request failed"
    )


def test_list_collector_runs(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        collector_runs,
        "collect_lba_offers",
        lambda: [build_collected_offer()],
    )

    run_response = authenticated_client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert run_response.status_code == 200

    history_response = authenticated_client.get(
        "/collectors/runs"
    )

    assert history_response.status_code == 200

    history = history_response.json()

    assert len(history) == 1
    assert history[0]["collector"] == (
        "la-bonne-alternance"
    )
    assert history[0]["trigger"] == "manual"
    assert history[0]["status"] == "completed"
    assert history[0]["found"] == 1
    assert history[0]["added"] == 1
    assert history[0]["finished_at"] is not None


def test_list_collector_runs_filters_status(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_api_error():
        raise CollectorAPIError(
            "La Bonne Alternance API request failed"
        )

    monkeypatch.setattr(
        collector_runs,
        "collect_lba_offers",
        raise_api_error,
    )

    run_response = authenticated_client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert run_response.status_code == 502

    failed_response = authenticated_client.get(
        "/collectors/runs",
        params={
            "status": "failed",
            "trigger": "manual",
        },
    )
    completed_response = authenticated_client.get(
        "/collectors/runs",
        params={
            "status": "completed",
        },
    )

    assert failed_response.status_code == 200
    assert len(failed_response.json()) == 1
    assert failed_response.json()[0]["status"] == (
        "failed"
    )

    assert completed_response.status_code == 200
    assert completed_response.json() == []
