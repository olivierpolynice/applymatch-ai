from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CandidateProfile, JobOffer, MatchResult
from app.services.application_automation import load_context
from app.services.document_generation import (
    draft_directory,
    generate_application_documents,
)


MANUAL_PLATFORMS = {
    "linkedin.com": "LinkedIn",
    "indeed.com": "Indeed",
    "indeed.fr": "Indeed",
    "apec.fr": "APEC",
    "welcometothejungle.com": "Welcome to the Jungle",
}


class BrowserAssistanceError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def platform_name(url: str) -> str:
    host = (urlparse(url).hostname or "").casefold()
    for domain, label in MANUAL_PLATFORMS.items():
        if host == domain or host.endswith(f".{domain}"):
            return label
    return "Plateforme externe"


def validated_source_url(value: str | None) -> str:
    if not value:
        raise BrowserAssistanceError("The offer has no source URL")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise BrowserAssistanceError("The offer source URL is invalid")
    return value


def prepare_browser_assistance(db: Session, *, draft_id: int) -> dict[str, Any]:
    draft, offer, match = load_context(db, draft_id)
    url = validated_source_url(offer.source_url)
    profile = db.get(CandidateProfile, draft.profile_id)
    if profile is None:
        raise BrowserAssistanceError(
            "Candidate profile not found", status_code=409
        )
    documents = generate_application_documents(
        draft=draft,
        profile=profile,
        offer=offer,
        match_result=match,
    )
    if not documents.validation.valid:
        raise BrowserAssistanceError(
            "Documents failed validation: "
            + "; ".join(documents.validation.errors)
        )
    base_url = f"/application-drafts/{draft.id}/documents"
    return {
        "draft_id": draft.id,
        "offer_id": offer.id,
        "platform": platform_name(url),
        "source_url": url,
        "mode": "human_validation_required",
        "cover_letter_docx_url": f"{base_url}/cover-letter-docx",
        "cover_letter_pdf_url": f"{base_url}/cover-letter-pdf",
        "adapted_cv_pdf_url": f"{base_url}/adapted-cv-pdf",
        "documents_valid": True,
        "instructions": [
            "Vérifie que l'offre et l'entreprise sont correctes.",
            "Connecte-toi toi-même si la plateforme le demande.",
            "Joins le CV et la lettre préparés.",
            "Réponds uniquement aux questions que tu connais.",
            "Vérifie puis envoie toi-même la candidature.",
            "Reviens dans ApplyMatch et confirme « J'ai postulé ».",
        ],
    }


def local_document_paths(db: Session, *, draft_id: int) -> dict[str, Path]:
    draft, _offer, _match = load_context(db, draft_id)
    directory = draft_directory(draft)
    return {
        "cv": directory / "cv-adapte.pdf",
        "letter_pdf": directory / "lettre-motivation.pdf",
        "letter_docx": directory / "lettre-motivation.docx",
    }


def open_assisted_browser(
    url: str,
    *,
    playwright_factory: Callable[[], Any] | None = None,
) -> None:
    validated_source_url(url)
    if playwright_factory is None:
        from playwright.sync_api import sync_playwright

        playwright_factory = sync_playwright
    with playwright_factory() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")
        print("Offre ouverte. ApplyMatch ne cliquera pas sur Envoyer.")
        input("Appuie sur Entrée après avoir terminé pour fermer Chromium...")
        browser.close()
