from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import MatchResult
from tests.test_candidate_profiles import PROFILE_DATA
from tests.test_job_offers import OFFER_DATA


def create_match(authenticated_client: TestClient) -> dict:
    profile_response = authenticated_client.post(
        "/candidate-profiles",
        json=PROFILE_DATA,
    )
    offer_response = authenticated_client.post(
        "/job-offers",
        json=OFFER_DATA,
    )

    assert profile_response.status_code == 201
    assert offer_response.status_code == 201

    profile = profile_response.json()
    offer = offer_response.json()

    match_response = authenticated_client.post(
        f"/matching/profile/{profile['id']}"
        f"/offer/{offer['id']}"
    )

    assert match_response.status_code == 200

    return match_response.json()


def add_match_to_queue(
    authenticated_client: TestClient,
    match_result_id: int,
) -> dict:
    response = authenticated_client.post(
        "/validation-queue",
        json={
            "match_result_id": match_result_id,
        },
    )

    assert response.status_code == 201

    return response.json()


def test_add_recommended_match_to_validation_queue(
    authenticated_client: TestClient,
) -> None:
    match_result = create_match(authenticated_client)

    response = authenticated_client.post(
        "/validation-queue",
        json={
            "match_result_id": match_result["id"],
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["profile_id"] == match_result["profile_id"]
    assert data["offer_id"] == match_result["offer_id"]
    assert data["match_result_id"] == match_result["id"]
    assert data["status"] == "pending"
    assert data["priority"] == (
        match_result["application_priority"]
    )
    assert data["reviewer_comment"] is None
    assert data["decided_at"] is None


def test_list_validation_queue_with_filters(
    authenticated_client: TestClient,
) -> None:
    match_result = create_match(authenticated_client)
    queue_item = add_match_to_queue(
        authenticated_client,
        match_result["id"],
    )

    included_response = authenticated_client.get(
        "/validation-queue",
        params={
            "status": "pending",
            "priority": queue_item["priority"],
        },
    )
    excluded_response = authenticated_client.get(
        "/validation-queue",
        params={"status": "rejected"},
    )

    assert included_response.status_code == 200
    assert len(included_response.json()) == 1
    assert included_response.json()[0]["id"] == (
        queue_item["id"]
    )

    assert excluded_response.status_code == 200
    assert excluded_response.json() == []


def test_get_validation_queue_item(
    authenticated_client: TestClient,
) -> None:
    match_result = create_match(authenticated_client)
    queue_item = add_match_to_queue(
        authenticated_client,
        match_result["id"],
    )

    response = authenticated_client.get(
        f"/validation-queue/{queue_item['id']}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == queue_item["id"]


def test_duplicate_match_is_rejected(
    authenticated_client: TestClient,
) -> None:
    match_result = create_match(authenticated_client)
    add_match_to_queue(authenticated_client, match_result["id"])

    response = authenticated_client.post(
        "/validation-queue",
        json={
            "match_result_id": match_result["id"],
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "This match is already in the "
            "validation queue"
        )
    }


def test_unknown_match_is_rejected(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.post(
        "/validation-queue",
        json={"match_result_id": 999},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Match result not found"
    }


def test_skip_match_is_not_eligible(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    match_result = create_match(authenticated_client)
    stored_match = db_session.get(
        MatchResult,
        match_result["id"],
    )

    assert stored_match is not None

    stored_match.decision = "skip"
    stored_match.application_priority = "low"
    db_session.commit()

    response = authenticated_client.post(
        "/validation-queue",
        json={
            "match_result_id": match_result["id"],
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "This match is not eligible for "
            "manual validation"
        )
    }


def test_approve_queue_item_without_sending_application(
    authenticated_client: TestClient,
) -> None:
    match_result = create_match(authenticated_client)
    queue_item = add_match_to_queue(
        authenticated_client,
        match_result["id"],
    )

    response = authenticated_client.patch(
        (
            f"/validation-queue/{queue_item['id']}"
            "/decision"
        ),
        json={
            "decision": "approved",
            "reviewer_comment": (
                "CV Ã  adapter avant toute candidature."
            ),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "approved"
    assert data["reviewer_comment"] == (
        "CV Ã  adapter avant toute candidature."
    )
    assert data["decided_at"] is not None

    offer_response = authenticated_client.get(
        f"/job-offers/{match_result['offer_id']}"
    )

    assert offer_response.status_code == 200
    assert offer_response.json()["status"] == "new"


def test_reject_queue_item(
    authenticated_client: TestClient,
) -> None:
    match_result = create_match(authenticated_client)
    queue_item = add_match_to_queue(
        authenticated_client,
        match_result["id"],
    )

    response = authenticated_client.patch(
        (
            f"/validation-queue/{queue_item['id']}"
            "/decision"
        ),
        json={
            "decision": "rejected",
            "reviewer_comment": "Offre non retenue.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["reviewer_comment"] == (
        "Offre non retenue."
    )


def test_final_decision_cannot_be_changed(
    authenticated_client: TestClient,
) -> None:
    match_result = create_match(authenticated_client)
    queue_item = add_match_to_queue(
        authenticated_client,
        match_result["id"],
    )
    endpoint = (
        f"/validation-queue/{queue_item['id']}"
        "/decision"
    )

    first_response = authenticated_client.patch(
        endpoint,
        json={"decision": "approved"},
    )
    second_response = authenticated_client.patch(
        endpoint,
        json={"decision": "rejected"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json() == {
        "detail": (
            "This validation queue item has "
            "already been decided"
        )
    }


def test_unknown_queue_item_returns_404(
    authenticated_client: TestClient,
) -> None:
    get_response = authenticated_client.get(
        "/validation-queue/999"
    )
    decision_response = authenticated_client.patch(
        "/validation-queue/999/decision",
        json={"decision": "approved"},
    )

    assert get_response.status_code == 404
    assert decision_response.status_code == 404
    assert get_response.json() == {
        "detail": "Validation queue item not found"
    }
    assert decision_response.json() == {
        "detail": "Validation queue item not found"
    }
