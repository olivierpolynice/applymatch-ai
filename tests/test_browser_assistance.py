from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import JobOffer
from app.services.browser_assistance import open_assisted_browser
from tests.test_application_automation import prepare_eligible_draft


def test_prepare_manual_platform_with_valid_documents(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    draft = prepare_eligible_draft(authenticated_client, db_session)
    offer = db_session.get(JobOffer, draft["offer_id"])
    assert offer is not None
    offer.source_url = "https://www.linkedin.com/jobs/view/123456"
    db_session.commit()

    response = authenticated_client.post(
        f"/browser-assistance/drafts/{draft['id']}/prepare"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "LinkedIn"
    assert data["mode"] == "human_validation_required"
    assert data["documents_valid"] is True
    assert data["adapted_cv_pdf_url"].endswith("/adapted-cv-pdf")
    assert any("envoie toi-même" in item for item in data["instructions"])


def test_offer_without_url_cannot_start_browser_assistance(
    authenticated_client: TestClient,
    db_session: Session,
) -> None:
    draft = prepare_eligible_draft(authenticated_client, db_session)
    offer = db_session.get(JobOffer, draft["offer_id"])
    assert offer is not None
    offer.source_url = None
    db_session.commit()

    response = authenticated_client.post(
        f"/browser-assistance/drafts/{draft['id']}/prepare"
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "The offer has no source URL"


def test_playwright_opens_offer_without_clicking_submit(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    class Page:
        def goto(self, url: str, **kwargs) -> None:
            events.append(("goto", url))

    class Browser:
        def new_page(self) -> Page:
            return Page()

        def close(self) -> None:
            events.append(("close", True))

    class Chromium:
        def launch(self, **kwargs) -> Browser:
            assert kwargs == {"headless": False}
            return Browser()

    class Playwright:
        chromium = Chromium()

    class Context:
        def __enter__(self) -> Playwright:
            return Playwright()

        def __exit__(self, *args) -> None:
            return None

    monkeypatch.setattr("builtins.input", lambda _message: "")
    open_assisted_browser(
        "https://www.apec.fr/offres/123",
        playwright_factory=lambda: Context(),
    )

    assert events == [
        ("goto", "https://www.apec.fr/offres/123"),
        ("close", True),
    ]
