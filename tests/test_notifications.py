from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.notifications import (
    create_notification,
    create_notification_once,
)


def test_list_notifications_is_empty(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get(
        "/notifications"
    )
    count_response = authenticated_client.get(
        "/notifications/unread-count"
    )

    assert response.status_code == 200
    assert response.json() == []

    assert count_response.status_code == 200
    assert count_response.json() == {
        "unread_count": 0,
    }


def test_list_unread_notifications(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    create_notification(
        db_session,
        notification_type="new_offers",
        level="success",
        title="Nouvelles offres",
        message="Deux nouvelles offres sont disponibles.",
        target_url="#offers",
    )

    response = authenticated_client.get(
        "/notifications",
        params={
            "unread_only": True,
            "notification_type": "new_offers",
        },
    )
    count_response = authenticated_client.get(
        "/notifications/unread-count"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["notification_type"] == (
        "new_offers"
    )
    assert data[0]["level"] == "success"
    assert data[0]["is_read"] is False
    assert data[0]["read_at"] is None
    assert data[0]["target_url"] == "#offers"

    assert count_response.status_code == 200
    assert count_response.json() == {
        "unread_count": 1,
    }


def test_mark_notification_as_read(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    notification = create_notification(
        db_session,
        notification_type="high_score",
        level="success",
        title="Offre compatible",
        message="Score de compatibilitÃ© : 85/100.",
        target_url="#match-1",
    )

    response = authenticated_client.patch(
        f"/notifications/{notification.id}/read"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == notification.id
    assert data["is_read"] is True
    assert data["read_at"] is not None

    count_response = authenticated_client.get(
        "/notifications/unread-count"
    )

    assert count_response.json() == {
        "unread_count": 0,
    }


def test_mark_all_notifications_as_read(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    create_notification(
        db_session,
        notification_type="new_offers",
        level="success",
        title="Nouvelles offres",
        message="Une nouvelle offre est disponible.",
        target_url="#offers",
    )
    create_notification(
        db_session,
        notification_type="draft_ready",
        level="info",
        title="Brouillon prÃªt",
        message="Le brouillon est prÃªt Ã  Ãªtre vÃ©rifiÃ©.",
        target_url="#draft-1-version-1",
    )

    response = authenticated_client.patch(
        "/notifications/read-all"
    )

    assert response.status_code == 200
    assert response.json() == {
        "unread_count": 0,
    }

    unread_response = authenticated_client.get(
        "/notifications",
        params={"unread_only": True},
    )

    assert unread_response.status_code == 200
    assert unread_response.json() == []


def test_unknown_notification_returns_404(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.patch(
        "/notifications/999/read"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Notification not found",
    }


def test_create_notification_once_is_idempotent(
    db_session: Session,
) -> None:
    first_notification, first_created = (
        create_notification_once(
            db_session,
            notification_type="high_score",
            level="success",
            title="Offre compatible",
            message="Score de compatibilitÃ© : 90/100.",
            target_url="#match-12",
        )
    )

    second_notification, second_created = (
        create_notification_once(
            db_session,
            notification_type="high_score",
            level="success",
            title="Offre compatible",
            message="Score de compatibilitÃ© : 90/100.",
            target_url="#match-12",
        )
    )

    assert first_created is True
    assert second_created is False
    assert second_notification.id == (
        first_notification.id
    )
