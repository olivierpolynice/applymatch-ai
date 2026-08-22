from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import JobOffer
from tests.test_application_automation import prepare_eligible_draft


class FakeRequest:
    def __init__(self, result: dict[str, str]) -> None:
        self.result = result

    def execute(self) -> dict[str, str]:
        return self.result


class FakeDrafts:
    def create(self, **kwargs: Any) -> FakeRequest:
        assert kwargs["userId"] == "me"
        assert kwargs["body"]["message"]["raw"]
        return FakeRequest({"id": "gmail-draft-001"})

    def send(self, **kwargs: Any) -> FakeRequest:
        assert kwargs == {
            "userId": "me",
            "body": {"id": "gmail-draft-001"},
        }
        return FakeRequest({"id": "gmail-message-001"})


class FakeUsers:
    def drafts(self) -> FakeDrafts:
        return FakeDrafts()


class FakeGmail:
    def users(self) -> FakeUsers:
        return FakeUsers()


def test_gmail_draft_does_not_mark_offer_as_applied(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    draft = prepare_eligible_draft(authenticated_client, db_session)
    monkeypatch.setattr(
        "app.services.gmail_delivery.gmail_client", lambda: FakeGmail()
    )

    response = authenticated_client.post(
        "/gmail/drafts",
        json={
            "draft_id": draft["id"],
            "recipient": "recrutement@example.com",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "draft_created"
    assert response.json()["gmail_message_id"] is None
    offer = db_session.get(JobOffer, draft["offer_id"])
    db_session.refresh(offer)
    assert offer.application_status != "sent"
    assert offer.status != "applied"


def test_only_confirmed_gmail_send_archives_application(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    draft = prepare_eligible_draft(authenticated_client, db_session)
    monkeypatch.setattr(
        "app.services.gmail_delivery.gmail_client", lambda: FakeGmail()
    )
    created = authenticated_client.post(
        "/gmail/drafts",
        json={
            "draft_id": draft["id"],
            "recipient": "recrutement@example.com",
        },
    ).json()

    sent = authenticated_client.post(
        f"/gmail/deliveries/{created['id']}/send"
    )

    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"
    assert sent.json()["gmail_message_id"] == "gmail-message-001"
    offer = db_session.get(JobOffer, draft["offer_id"])
    db_session.refresh(offer)
    assert offer.status == "applied"
    assert offer.application_status == "sent"
    assert offer.provider_confirmation_id == "gmail-message-001"


def test_gmail_without_confirmation_is_not_archived(
    authenticated_client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    class UnconfirmedDrafts(FakeDrafts):
        def send(self, **kwargs: Any) -> FakeRequest:
            return FakeRequest({})

    class UnconfirmedUsers:
        def drafts(self) -> UnconfirmedDrafts:
            return UnconfirmedDrafts()

    class UnconfirmedGmail:
        def users(self) -> UnconfirmedUsers:
            return UnconfirmedUsers()

    draft = prepare_eligible_draft(authenticated_client, db_session)
    monkeypatch.setattr(
        "app.services.gmail_delivery.gmail_client", lambda: FakeGmail()
    )
    created = authenticated_client.post(
        "/gmail/drafts",
        json={
            "draft_id": draft["id"],
            "recipient": "recrutement@example.com",
        },
    ).json()
    monkeypatch.setattr(
        "app.services.gmail_delivery.gmail_client",
        lambda: UnconfirmedGmail(),
    )

    sent = authenticated_client.post(
        f"/gmail/deliveries/{created['id']}/send"
    )

    assert sent.status_code == 502
    offer = db_session.get(JobOffer, draft["offer_id"])
    db_session.refresh(offer)
    assert offer.status != "applied"
    assert offer.provider_confirmation_id is None
