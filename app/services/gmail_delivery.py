import base64
import json
import logging
import os
import re
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CandidateProfile, GmailDelivery
from app.models.gmail_delivery import utc_now
from app.services.application_automation import (
    ApplicationAutomationError,
    archive_confirmed_application,
    evaluate_automation,
    load_context,
)
from app.services.document_generation import (
    draft_directory,
    generate_application_documents,
)
from app.observability import log_event


logger = logging.getLogger(__name__)


GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class GmailDeliveryError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def client_config() -> dict:
    client_id = os.getenv("GMAIL_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GMAIL_OAUTH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise GmailDeliveryError(
            "GMAIL_OAUTH_CLIENT_ID / GMAIL_OAUTH_CLIENT_SECRET "
            "are not configured",
            status_code=503,
        )
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri()],
        }
    }


def redirect_uri() -> str:
    return os.getenv(
        "GMAIL_OAUTH_REDIRECT_URI", "http://localhost:8000/docs"
    ).strip()


def authorization_url() -> tuple[str, str, str]:
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        client_config(), scopes=GMAIL_SCOPES
    )
    flow.redirect_uri = redirect_uri()
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url, state, flow.code_verifier


def exchange_authorization_code(
    code: str, code_verifier: str
) -> None:
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        client_config(), scopes=GMAIL_SCOPES
    )
    flow.redirect_uri = redirect_uri()
    flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    save_token(flow.credentials.to_json())


def save_token(token_json: str, db: Session | None = None) -> None:
    from app.db.session import SessionLocal
    from app.models import OAuthToken

    owns_session = db is None
    session = db or SessionLocal()
    try:
        record = session.scalar(
            select(OAuthToken).where(OAuthToken.provider == "gmail")
        )
        if record is None:
            record = OAuthToken(provider="gmail", token_json=token_json)
            session.add(record)
        else:
            record.token_json = token_json
        session.commit()
    finally:
        if owns_session:
            session.close()


def load_token(db: Session | None = None) -> str | None:
    from app.db.session import SessionLocal
    from app.models import OAuthToken

    owns_session = db is None
    session = db or SessionLocal()
    try:
        record = session.scalar(
            select(OAuthToken).where(OAuthToken.provider == "gmail")
        )
        return record.token_json if record else None
    finally:
        if owns_session:
            session.close()


def is_connected() -> bool:
    return load_token() is not None


def gmail_client() -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_json = load_token()
    if token_json is None:
        raise GmailDeliveryError(
            "Gmail is not connected. Complete Google OAuth first.",
            status_code=409,
        )
    credentials = Credentials.from_authorized_user_info(
        json.loads(token_json), GMAIL_SCOPES
    )
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_token(credentials.to_json())
    if not credentials.valid:
        raise GmailDeliveryError(
            "Gmail authorization is invalid or expired", status_code=409
        )
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def _raw_message(
    *, recipient: str, subject: str, body: str, attachments: list[Path]
) -> str:
    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    for path in attachments:
        message.add_attachment(
            path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=path.name,
        )
    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def create_gmail_draft(
    db: Session,
    *,
    draft_id: int,
    recipient: str,
    client: Any | None = None,
) -> GmailDelivery:
    log_event(logger, "gmail_draft_creation_started", draft_id=draft_id)
    recipient = recipient.strip().casefold()
    if not EMAIL_PATTERN.fullmatch(recipient):
        raise GmailDeliveryError("A valid recruitment email is required")
    existing = db.scalar(
        select(GmailDelivery).where(GmailDelivery.draft_id == draft_id)
    )
    if existing is not None:
        raise GmailDeliveryError(
            "A Gmail draft already exists for this application",
            status_code=409,
        )

    draft, offer, match = load_context(db, draft_id)
    profile = db.get(CandidateProfile, draft.profile_id)
    if profile is None:
        raise GmailDeliveryError("Candidate profile not found", status_code=409)
    documents = generate_application_documents(
        draft=draft, profile=profile, offer=offer, match_result=match
    )
    if not documents.validation.valid:
        raise GmailDeliveryError(
            "Documents failed validation: "
            + "; ".join(documents.validation.errors)
        )
    documents_directory = draft_directory(draft)
    raw = _raw_message(
        recipient=recipient,
        subject=f"Candidature – {offer.title} – {profile.full_name}",
        body=draft.short_message,
        attachments=[
            documents_directory / documents.adapted_cv_pdf,
            documents_directory / documents.cover_letter_pdf,
        ],
    )
    response = (client or gmail_client()).users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()
    gmail_draft_id = str(response.get("id", "")).strip()
    if not gmail_draft_id:
        raise GmailDeliveryError(
            "Gmail did not confirm draft creation", status_code=502
        )
    delivery = GmailDelivery(
        draft_id=draft.id,
        recipient=recipient,
        gmail_draft_id=gmail_draft_id,
        status="draft_created",
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    log_event(
        logger,
        "gmail_draft_created",
        draft_id=draft_id,
        delivery_id=delivery.id,
        gmail_draft_id=gmail_draft_id,
    )
    return delivery


def send_gmail_draft(
    db: Session,
    *,
    delivery_id: int,
    automatic: bool = False,
    client: Any | None = None,
) -> GmailDelivery:
    log_event(
        logger,
        "gmail_send_attempted",
        delivery_id=delivery_id,
        automatic=automatic,
    )
    delivery = db.get(GmailDelivery, delivery_id)
    if delivery is None:
        raise GmailDeliveryError("Gmail delivery not found", status_code=404)
    if delivery.status == "sent":
        raise GmailDeliveryError("This Gmail draft was already sent", status_code=409)

    if automatic:
        evaluation = evaluate_automation(
            db,
            draft_id=delivery.draft_id,
            channel="recruitment_email",
            channel_authorized=True,
            has_unknown_questions=False,
        )
        if not evaluation["eligible"]:
            raise GmailDeliveryError(
                "Automatic Gmail send blocked: "
                + "; ".join(evaluation["reasons"])
            )

    response = (client or gmail_client()).users().drafts().send(
        userId="me", body={"id": delivery.gmail_draft_id}
    ).execute()
    message_id = str(response.get("id", "")).strip()
    if not message_id:
        raise GmailDeliveryError(
            "Gmail did not confirm message delivery", status_code=502
        )

    delivery.gmail_message_id = message_id
    delivery.status = "sent"
    delivery.sent_at = utc_now()
    try:
        archive_confirmed_application(
            db,
            draft_id=delivery.draft_id,
            channel="recruitment_email",
            channel_authorized=True,
            has_unknown_questions=False,
            provider_confirmation_id=message_id,
            application_mode="automatic" if automatic else "manual",
        )
    except ApplicationAutomationError as error:
        raise GmailDeliveryError(
            error.message, status_code=error.status_code
        ) from error
    db.refresh(delivery)
    log_event(
        logger,
        "gmail_send_confirmed",
        delivery_id=delivery.id,
        draft_id=delivery.draft_id,
        gmail_message_id=message_id,
    )
    return delivery