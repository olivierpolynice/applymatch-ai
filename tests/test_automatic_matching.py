import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import (
    ApplicationDraft,
    CandidateProfile,
    CollectorRun,
    MatchResult,
    Notification,
    ValidationQueueItem,
)
from app.schemas import JobOfferCreate
from app.services import collector_runs


def build_active_profile(
    db: Session,
) -> CandidateProfile:
    db.execute(
        update(CandidateProfile).values(
            is_active=False,
        )
    )

    profile = CandidateProfile(
        full_name="Olivier Polynice",
        education_level="Bac+5",
        program=(
            "Master Réseaux, Cybersécurité "
            "et Cloud"
        ),
        target_contract="Alternance",
        availability="septembre 2026",
        work_schedule=(
            "4 jours en entreprise, "
            "1 jour à l'école"
        ),
        location="Île-de-France",
        target_roles=(
            "Cloud, cybersécurité, DevSecOps, "
            "intelligence artificielle"
        ),
        skills=(
            "Python, FastAPI, cloud, Docker, "
            "intelligence artificielle"
        ),
        professional_summary=None,
        experience_highlights=None,
        project_highlights=None,
        is_active=True,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile


def build_high_score_offer() -> JobOfferCreate:
    return JobOfferCreate(
        title=(
            "Alternance Ingénieur IA et Cloud"
        ),
        company="Entreprise Innovation",
        location="Paris 75007",
        contract_type="Apprentissage",
        description=(
            "Développement Python et FastAPI de "
            "solutions d'intelligence artificielle "
            "sur une plateforme cloud avec Docker."
        ),
        source="La Bonne Alternance",
        source_url=(
            "https://example.com/offers/"
            "automatic-ai-cloud"
        ),
        published_at=None,
    )


def count_rows(
    db: Session,
    model: type,
) -> int:
    value = db.scalar(
        select(func.count()).select_from(model)
    )

    return int(value or 0)


def test_collection_creates_match_automatically(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = build_active_profile(
        db_session,
    )

    monkeypatch.setattr(
        collector_runs,
        "collect_lba_offers",
        lambda: [build_high_score_offer()],
    )

    response = authenticated_client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert response.status_code == 200
    assert response.json()["added"] == 1

    result = db_session.scalar(
        select(MatchResult)
    )

    assert result is not None
    assert result.profile_id == profile.id
    assert result.score >= 70
    assert result.decision == "documents_ready"

    high_score_notification = db_session.scalar(
        select(Notification).where(
            Notification.notification_type
            == "high_score"
        )
    )

    assert high_score_notification is not None
    assert high_score_notification.target_url == (
        f"#match-{result.id}"
    )

    assert count_rows(
        db_session,
        ValidationQueueItem,
    ) == 1
    assert count_rows(
        db_session,
        ApplicationDraft,
    ) == 1


def test_duplicate_collection_does_not_rematch(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_active_profile(db_session)
    offer = build_high_score_offer()

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
    assert second_response.json()["added"] == 0
    assert second_response.json()["duplicates"] == 1

    assert count_rows(
        db_session,
        MatchResult,
    ) == 1

    high_score_count = db_session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.notification_type
            == "high_score"
        )
    )

    assert high_score_count == 1


def test_matching_failure_does_not_fail_collection(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_active_profile(db_session)

    monkeypatch.setattr(
        collector_runs,
        "collect_lba_offers",
        lambda: [build_high_score_offer()],
    )

    def raise_matching_error(*args, **kwargs):
        raise RuntimeError(
            "Automatic matching failure"
        )

    monkeypatch.setattr(
        collector_runs,
        "match_new_offers",
        raise_matching_error,
    )

    response = authenticated_client.post(
        "/collectors/la-bonne-alternance/run"
    )

    assert response.status_code == 200
    assert response.json()["added"] == 1

    stored_run = db_session.scalar(
        select(CollectorRun)
    )

    assert stored_run is not None
    assert stored_run.status == "completed"
    assert stored_run.added == 1
    assert count_rows(
        db_session,
        MatchResult,
    ) == 0