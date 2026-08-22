import os

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth_dependencies import get_current_admin
from app.background.celery_app import celery_app
from app.background.tasks import (
    collect_offers,
    daily_report,
    generate_documents,
    send_gmail,
)
from app.schemas import BackgroundTaskRead, BackgroundTaskStatusRead


router = APIRouter(
    prefix="/background-tasks",
    tags=["Background tasks"],
    dependencies=[Depends(get_current_admin)],
)


def ensure_enabled() -> None:
    enabled = os.getenv("BACKGROUND_TASKS_ENABLED", "false").strip().casefold()
    if enabled not in {"1", "true", "yes", "on"}:
        raise HTTPException(
            status_code=503,
            detail="Background tasks are disabled",
        )


def queued(task_id: str, task_type: str) -> dict[str, str]:
    return {"task_id": task_id, "status": "queued", "task_type": task_type}


@router.post("/collect-offers", response_model=BackgroundTaskRead, status_code=202)
def enqueue_collection() -> dict[str, str]:
    ensure_enabled()
    task_id = "collect-offers-manual"
    collect_offers.apply_async(task_id=task_id)
    return queued(task_id, "collect_offers")


@router.post(
    "/drafts/{draft_id}/documents",
    response_model=BackgroundTaskRead,
    status_code=202,
)
def enqueue_documents(draft_id: int) -> dict[str, str]:
    ensure_enabled()
    task_id = f"documents-draft-{draft_id}"
    generate_documents.apply_async(args=[draft_id], task_id=task_id)
    return queued(task_id, "generate_documents")


@router.post(
    "/gmail/{delivery_id}/send",
    response_model=BackgroundTaskRead,
    status_code=202,
)
def enqueue_gmail(delivery_id: int, automatic: bool = False) -> dict[str, str]:
    ensure_enabled()
    task_id = f"gmail-delivery-{delivery_id}"
    send_gmail.apply_async(
        args=[delivery_id, automatic], task_id=task_id
    )
    return queued(task_id, "send_gmail")


@router.post("/daily-report", response_model=BackgroundTaskRead, status_code=202)
def enqueue_daily_report() -> dict[str, str]:
    ensure_enabled()
    task_id = f"daily-report-manual"
    daily_report.apply_async(task_id=task_id)
    return queued(task_id, "daily_report")


@router.get("/{task_id}", response_model=BackgroundTaskStatusRead)
def task_status(task_id: str) -> dict:
    ensure_enabled()
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": result.result if result.ready() else None,
    }
