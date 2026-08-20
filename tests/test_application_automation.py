from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import MatchResult
from tests.test_application_drafts import (
    create_approved_queue_item,
    create_draft,
)


def prepare_eligible_draft(
    client: TestClient,
    db: Session,
) -> dict:
    match, queue_item = create_approved_queue_item(client)
    draft = create_draft(client, queue_item["id"])
    result = db.get(MatchResult, match["id"])
    assert result is not None
    result.score = 92
    result.role_match = True
    result.location_match = True
    result.contract_match = True
    result.missing_skills = []
    db.commit()
    return draft


def test_low_score_requires_manual_approval(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    match, queue_item = create_approved_queue_item(authenticated_client)
    draft = create_draft(authenticated_client, queue_item["id"])
    result = db_session.get(MatchResult, match["id"])
    assert result is not None
    result.score = 40
    db_session.commit()

    response = authenticated_client.post(
        "/application-automation/evaluate",
        json={
            "draft_id": draft["id"],
            "channel": "official_api",
            "channel_authorized": True,
            "has_unknown_questions": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["eligible"] is False
    assert response.json()["mode"] == "manual_approval"
    assert response.json()["reasons"]


def test_confirmed_automatic_application_archives_cv(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    draft = prepare_eligible_draft(authenticated_client, db_session)
    payload = {
        "draft_id": draft["id"],
        "channel": "official_api",
        "channel_authorized": True,
        "has_unknown_questions": False,
    }

    evaluation = authenticated_client.post(
        "/application-automation/evaluate", json=payload
    )
    assert evaluation.status_code == 200
    assert evaluation.json() == {
        "mode": "automatic",
        "eligible": True,
        "reasons": [],
    }

    confirmed = authenticated_client.post(
        "/application-automation/confirm-sent",
        json={
            **payload,
            "application_mode": "automatic",
            "provider_confirmation_id": "api-confirmation-001",
        },
    )
    assert confirmed.status_code == 201
    archive = confirmed.json()
    assert archive["application_mode"] == "automatic"
    assert archive["cv_snapshot"]
    assert archive["cover_letter_snapshot"]
    assert archive["sent_at"]

    archives = authenticated_client.get(
        "/application-automation/archives"
    )
    assert archives.status_code == 200
    assert archives.json()[0]["draft_id"] == draft["id"]

    offer = authenticated_client.get(
        f"/job-offers/{draft['offer_id']}"
    )
    assert offer.json()["status"] == "applied"


def test_unknown_question_blocks_automatic_confirmation(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    draft = prepare_eligible_draft(authenticated_client, db_session)
    response = authenticated_client.post(
        "/application-automation/confirm-sent",
        json={
            "draft_id": draft["id"],
            "channel": "official_api",
            "channel_authorized": True,
            "has_unknown_questions": True,
            "application_mode": "automatic",
            "provider_confirmation_id": "must-not-be-archived",
        },
    )
    assert response.status_code == 422
    assert "question inconnue" in response.json()["detail"]
