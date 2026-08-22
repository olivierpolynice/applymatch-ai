import base64
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


def client_secret_path() -> Path:
    value = os.getenv("GMAIL_CLIENT_SECRET_FILE", "").strip()
    if not value:
        raise GmailDeliveryError(
            "GMAIL_CLIENT_SECRET_FILE is not configured", status_code=503
        )
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise GmailDeliveryError(
            "Google OAuth client secret file was not found", status_code=503
        )
    return path


def token_path() -> Path:
    value = os.getenv("GMAIL_TOKEN_FILE", "secrets/gmail-token.json").strip()
    return Path(value).expanduser().resolve()


def redirect_uri() -> str:
    return os.getenv(
        "GMAIL_OAUTH_REDIRECT_URI", "http://localhost:8000/docs"
    ).strip()


def authorization_url() -> tuple[str, str]:
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(
        str(client_secret_path()), scopes=GMAIL_SCOPES
    )
    flow.redirect_uri = redirect_uri()
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url, state


def exchange_authorization_code(code: str) -> None:
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(
        str(client_secret_path()), scopes=GMAIL_SCOPES
    )
    flow.redirect_uri = redirect_uri()
    flow.fetch_token(code=code)
    destination = token_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(flow.credentials.to_json(), encoding="utf-8")


def is_connected() -> bool:
    return token_path().is_file()


def gmail_client() -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    path = token_path()
    if not path.is_file():
        raise GmailDeliveryError(
            "Gmail is not connected. Complete Google OAuth first.",
            status_code=409,
        )
    credentials = Credentials.from_authorized_user_file(
        str(path), GMAIL_SCOPES
    )
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        path.write_text(credentials.to_json(), encoding="utf-8")
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
