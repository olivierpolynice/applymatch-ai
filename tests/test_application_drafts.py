from fastapi.testclient import TestClient

from tests.test_validation_queue import (
    add_match_to_queue,
    create_match,
)


def create_approved_queue_item(
    client: TestClient,
) -> tuple[dict, dict]:
    match_result = create_match(client)
    queue_item = add_match_to_queue(
        client,
        match_result["id"],
    )

    approval_response = client.patch(
        (
            f"/validation-queue/{queue_item['id']}"
            "/decision"
        ),
        json={
            "decision": "approved",
            "reviewer_comment": (
                "Documents à relire avant toute candidature."
            ),
        },
    )

    assert approval_response.status_code == 200

    return match_result, approval_response.json()


def create_draft(
    client: TestClient,
    queue_item_id: int,
) -> dict:
    response = client.post(
        "/application-drafts",
        json={
            "validation_queue_item_id": queue_item_id,
        },
    )

    assert response.status_code == 201

    return response.json()


def test_draft_generation_requires_manual_approval(
    client: TestClient,
) -> None:
    match_result = create_match(client)
    queue_item = add_match_to_queue(
        client,
        match_result["id"],
    )

    response = client.post(
        "/application-drafts",
        json={
            "validation_queue_item_id": queue_item["id"],
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "The application must be manually approved "
            "before generating documents"
        )
    }


def test_create_application_draft(
    client: TestClient,
) -> None:
    match_result, queue_item = (
        create_approved_queue_item(client)
    )

    response = client.post(
        "/application-drafts",
        json={
            "validation_queue_item_id": queue_item["id"],
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["validation_queue_item_id"] == queue_item["id"]
    assert data["profile_id"] == match_result["profile_id"]
    assert data["offer_id"] == match_result["offer_id"]
    assert data["status"] == "draft"
    assert data["version"] == 1
    assert "Akuo" in data["cover_letter"]
    assert (
        "Alternance Network & Security Administrator"
        in data["cover_letter"]
    )
    assert "Olivier Polynice" in data["cover_letter"]
    assert "Akuo" in data["short_message"]
    assert "Adapter le titre du CV" in (
        data["cv_adaptation_tips"]
    )
    assert data["generated_at"] is not None


def test_duplicate_draft_is_rejected(
    client: TestClient,
) -> None:
    _, queue_item = create_approved_queue_item(client)
    create_draft(client, queue_item["id"])

    response = client.post(
        "/application-drafts",
        json={
            "validation_queue_item_id": queue_item["id"],
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "An application draft already exists "
            "for this validation"
        )
    }


def test_unknown_validation_queue_item_returns_404(
    client: TestClient,
) -> None:
    response = client.post(
        "/application-drafts",
        json={"validation_queue_item_id": 999},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Validation queue item not found"
    }


def test_list_and_get_application_drafts(
    client: TestClient,
) -> None:
    _, queue_item = create_approved_queue_item(client)
    draft = create_draft(client, queue_item["id"])

    list_response = client.get(
        "/application-drafts",
        params={
            "status": "draft",
            "profile_id": draft["profile_id"],
        },
    )
    get_response = client.get(
        f"/application-drafts/{draft['id']}"
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == draft["id"]
    assert get_response.status_code == 200
    assert get_response.json()["id"] == draft["id"]


def test_update_application_draft_manually(
    client: TestClient,
) -> None:
    _, queue_item = create_approved_queue_item(client)
    draft = create_draft(client, queue_item["id"])

    updated_letter = (
        "Objet : Candidature personnalisée\n\n"
        "Madame, Monsieur, cette lettre a été relue et "
        "modifiée manuellement avant toute candidature."
    )
    updated_message = (
        "Bonjour, ce message de candidature a été relu "
        "et validé manuellement."
    )

    response = client.patch(
        f"/application-drafts/{draft['id']}",
        json={
            "cover_letter": updated_letter,
            "short_message": updated_message,
            "status": "reviewed",
        },
    )

    assert response.status_code == 200
    assert response.json()["cover_letter"] == updated_letter
    assert response.json()["short_message"] == updated_message
    assert response.json()["status"] == "reviewed"
    assert response.json()["version"] == 1


def test_regenerate_application_draft(
    client: TestClient,
) -> None:
    _, queue_item = create_approved_queue_item(client)
    draft = create_draft(client, queue_item["id"])

    manual_response = client.patch(
        f"/application-drafts/{draft['id']}",
        json={
            "cover_letter": (
                "Cette lettre temporaire a été modifiée "
                "manuellement avant la régénération complète."
            ),
            "status": "reviewed",
        },
    )

    assert manual_response.status_code == 200

    response = client.post(
        f"/application-drafts/{draft['id']}/regenerate"
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert response.json()["status"] == "draft"
    assert "Akuo" in response.json()["cover_letter"]
    assert response.json()["cover_letter"] != (
        manual_response.json()["cover_letter"]
    )


def test_generating_draft_does_not_send_application(
    client: TestClient,
) -> None:
    match_result, queue_item = (
        create_approved_queue_item(client)
    )
    create_draft(client, queue_item["id"])

    offer_response = client.get(
        f"/job-offers/{match_result['offer_id']}"
    )
    queue_response = client.get(
        f"/validation-queue/{queue_item['id']}"
    )

    assert offer_response.status_code == 200
    assert offer_response.json()["status"] == "new"
    assert queue_response.status_code == 200
    assert queue_response.json()["status"] == "approved"


def test_unknown_application_draft_returns_404(
    client: TestClient,
) -> None:
    get_response = client.get(
        "/application-drafts/999"
    )
    update_response = client.patch(
        "/application-drafts/999",
        json={"status": "reviewed"},
    )
    regenerate_response = client.post(
        "/application-drafts/999/regenerate"
    )

    assert get_response.status_code == 404
    assert update_response.status_code == 404
    assert regenerate_response.status_code == 404
    assert get_response.json() == {
        "detail": "Application draft not found"
    }
    assert update_response.json() == {
        "detail": "Application draft not found"
    }
    assert regenerate_response.json() == {
        "detail": "Application draft not found"
    }