from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_admin
from app.db.session import get_db
from app.models import GmailDelivery
from app.schemas import (
    GmailAuthorizationCodeCreate,
    GmailAuthorizationRead,
    GmailConnectionRead,
    GmailDeliveryRead,
    GmailDraftCreate,
)
from app.services.gmail_delivery import (
    GmailDeliveryError,
    authorization_url,
    create_gmail_draft,
    exchange_authorization_code,
    is_connected,
    send_gmail_draft,
)


router = APIRouter(
    prefix="/gmail",
    tags=["Gmail"],
    dependencies=[Depends(get_current_admin)],
)


def as_http_error(error: GmailDeliveryError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.message)


@router.get("/connection", response_model=GmailConnectionRead)
def connection_status() -> dict[str, bool]:
    return {"connected": is_connected()}


@router.post("/oauth/authorize", response_model=GmailAuthorizationRead)
def authorize() -> dict[str, str]:
    try:
        url, state, code_verifier = authorization_url()
        return {
            "authorization_url": url,
            "state": state,
            "code_verifier": code_verifier,
        }
    except GmailDeliveryError as error:
        raise as_http_error(error) from error


@router.post("/oauth/callback", response_model=GmailConnectionRead)
def oauth_callback(data: GmailAuthorizationCodeCreate) -> dict[str, bool]:
    try:
        exchange_authorization_code(data.code, data.code_verifier)
        return {"connected": True}
    except GmailDeliveryError as error:
        raise as_http_error(error) from error


@router.post("/drafts", response_model=GmailDeliveryRead, status_code=201)
def create_draft(
    data: GmailDraftCreate,
    db: Session = Depends(get_db),
) -> GmailDelivery:
    try:
        return create_gmail_draft(db, **data.model_dump())
    except GmailDeliveryError as error:
        raise as_http_error(error) from error


@router.post(
    "/deliveries/{delivery_id}/send",
    response_model=GmailDeliveryRead,
)
def send_draft(
    delivery_id: int,
    automatic: bool = False,
    db: Session = Depends(get_db),
) -> GmailDelivery:
    try:
        return send_gmail_draft(
            db, delivery_id=delivery_id, automatic=automatic
        )
    except GmailDeliveryError as error:
        raise as_http_error(error) from error


@router.get("/deliveries", response_model=list[GmailDeliveryRead])
def list_deliveries(db: Session = Depends(get_db)) -> list[GmailDelivery]:
    return list(
        db.scalars(
            select(GmailDelivery).order_by(GmailDelivery.created_at.desc())
        )
    )
