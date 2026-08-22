import os
from sqlalchemy import select

from app.background.celery_app import celery_app
from app.background.redis_coordinator import (
    RedisCoordinator,
    TaskAlreadyRunning,
)
from app.db.session import SessionLocal
from app.models import (
    ApplicationArchive,
    ApplicationDraft,
    CandidateProfile,
    GmailDelivery,
    JobOffer,
    MatchResult,
)
from app.services.collector_runs import execute_all_collector_runs
from app.services.document_generation import generate_application_documents
from app.services.gmail_delivery import GmailDeliveryError, send_gmail_draft
from app.services.daily_report import build_daily_report


def lock_seconds() -> int:
    try:
        return max(int(os.getenv("BACKGROUND_LOCK_SECONDS", "900")), 30)
    except ValueError:
        return 900


@celery_app.task(
    bind=True,
    name="applymatch.collect_offers",
    max_retries=5,
    default_retry_delay=60,
)
def collect_offers(self) -> dict:
    coordinator = RedisCoordinator()
    try:
        with coordinator.lock("collect-offers", expires=lock_seconds()):
            with SessionLocal() as db:
                result = execute_all_collector_runs(db, trigger="scheduled")
                return {
                    "found": result.found,
                    "added": result.added,
                    "duplicates": result.duplicates,
                    "errors": result.errors,
                }
    except TaskAlreadyRunning:
        return {"status": "already_running"}
    except (ConnectionError, TimeoutError) as error:
        raise self.retry(exc=error, countdown=min(60 * (2**self.request.retries), 900))


@celery_app.task(
    bind=True,
    name="applymatch.generate_documents",
    max_retries=3,
)
def generate_documents(self, draft_id: int) -> dict:
    coordinator = RedisCoordinator()
    try:
        with coordinator.lock(
            f"documents:{draft_id}", expires=lock_seconds()
        ):
            with SessionLocal() as db:
                draft = db.get(ApplicationDraft, draft_id)
                if draft is None:
                    return {"status": "not_found"}
                profile = db.get(CandidateProfile, draft.profile_id)
                offer = db.get(JobOffer, draft.offer_id)
                match = db.scalar(
                    select(MatchResult).where(
                        MatchResult.profile_id == draft.profile_id,
                        MatchResult.offer_id == draft.offer_id,
                    )
                )
                if profile is None or offer is None or match is None:
                    return {"status": "incomplete_context"}
                result = generate_application_documents(
                    draft=draft,
                    profile=profile,
                    offer=offer,
                    match_result=match,
                )
                return {
                    "status": "completed",
                    "valid": result.validation.valid,
                    "errors": result.validation.errors,
                }
    except TaskAlreadyRunning:
        return {"status": "already_running"}


@celery_app.task(
    bind=True,
    name="applymatch.send_gmail",
    max_retries=5,
    default_retry_delay=60,
)
def send_gmail(self, delivery_id: int, automatic: bool = False) -> dict:
    coordinator = RedisCoordinator()
    try:
        with coordinator.lock(
            f"gmail:{delivery_id}", expires=lock_seconds()
        ):
            with SessionLocal() as db:
                delivery = db.get(GmailDelivery, delivery_id)
                if delivery is None:
                    return {"status": "not_found"}
                if delivery.status == "sent" and delivery.gmail_message_id:
                    return {
                        "status": "already_sent",
                        "message_id": delivery.gmail_message_id,
                    }
                delivery = send_gmail_draft(
                    db,
                    delivery_id=delivery_id,
                    automatic=automatic,
                )
                return {
                    "status": "sent",
                    "message_id": delivery.gmail_message_id,
                }
    except TaskAlreadyRunning:
        return {"status": "already_running"}
    except GmailDeliveryError as error:
        if error.status_code in {502, 503}:
            raise self.retry(
                exc=error,
                countdown=min(60 * (2**self.request.retries), 900),
            )
        raise


@celery_app.task(name="applymatch.daily_report")
def daily_report() -> dict:
    with SessionLocal() as db:
        return build_daily_report(db)
