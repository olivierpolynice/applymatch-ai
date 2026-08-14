import logging
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CollectorRun
from app.services.collectors.la_bonne_alternance import (
    collect_lba_offers,
)
from app.services.notifications import (
    create_notification,
)
from app.services.offer_importer import (
    ImportResult,
    import_job_offers,
)


logger = logging.getLogger(__name__)

CollectorTrigger = Literal[
    "manual",
    "scheduled",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_collector_run(
    db: Session,
    *,
    trigger: CollectorTrigger,
) -> CollectorRun:
    collector_run = CollectorRun(
        collector="la-bonne-alternance",
        trigger=trigger,
        status="running",
        found=0,
        added=0,
        duplicates=0,
        errors=0,
    )

    db.add(collector_run)
    db.commit()
    db.refresh(collector_run)

    return collector_run


def complete_collector_run(
    db: Session,
    *,
    collector_run: CollectorRun,
    result: ImportResult,
) -> CollectorRun:
    collector_run.status = "completed"
    collector_run.found = result.found
    collector_run.added = result.added
    collector_run.duplicates = result.duplicates
    collector_run.errors = result.errors
    collector_run.error_message = None
    collector_run.finished_at = utc_now()

    db.commit()
    db.refresh(collector_run)

    return collector_run


def fail_collector_run(
    db: Session,
    *,
    collector_run: CollectorRun,
    error: Exception,
) -> CollectorRun:
    db.rollback()

    stored_run = db.get(
        CollectorRun,
        collector_run.id,
    )

    if stored_run is None:
        raise RuntimeError(
            "Collector run could not be reloaded"
        ) from error

    stored_run.status = "failed"
    stored_run.errors = max(
        stored_run.errors,
        1,
    )
    stored_run.error_message = (
        str(error)[:2000]
        or error.__class__.__name__
    )
    stored_run.finished_at = utc_now()

    db.commit()
    db.refresh(stored_run)

    return stored_run


def create_success_notification(
    db: Session,
    *,
    result: ImportResult,
) -> None:
    if result.added <= 0:
        return

    offer_label = (
        "offre a été ajoutée"
        if result.added == 1
        else "offres ont été ajoutées"
    )

    try:
        create_notification(
            db,
            notification_type="new_offers",
            level="success",
            title="Nouvelles offres disponibles",
            message=(
                f"{result.added} {offer_label} "
                "par La Bonne Alternance."
            ),
            target_url="#offers",
        )
    except Exception:
        db.rollback()

        logger.exception(
            "Unable to create new offers notification."
        )


def create_failure_notification(
    db: Session,
    *,
    error: Exception,
) -> None:
    try:
        create_notification(
            db,
            notification_type="system_error",
            level="error",
            title="Échec de la collecte",
            message=(
                "La collecte La Bonne Alternance "
                f"a échoué : {str(error)[:500]}"
            ),
            target_url="#collector",
        )
    except Exception:
        db.rollback()

        logger.exception(
            "Unable to create collector failure notification."
        )


def execute_collector_run(
    db: Session,
    *,
    trigger: CollectorTrigger,
) -> tuple[CollectorRun, ImportResult]:
    collector_run = create_collector_run(
        db,
        trigger=trigger,
    )

    try:
        offers = collect_lba_offers()

        result = import_job_offers(
            db=db,
            offers=offers,
        )
    except Exception as error:
        failed_run = fail_collector_run(
            db,
            collector_run=collector_run,
            error=error,
        )

        create_failure_notification(
            db,
            error=error,
        )

        logger.error(
            "Collector run %s failed.",
            failed_run.id,
        )

        raise

    completed_run = complete_collector_run(
        db,
        collector_run=collector_run,
        result=result,
    )

    create_success_notification(
        db,
        result=result,
    )

    return completed_run, result


def list_collector_runs(
    db: Session,
    *,
    limit: int = 20,
    trigger: CollectorTrigger | None = None,
    status: str | None = None,
) -> list[CollectorRun]:
    statement = (
        select(CollectorRun)
        .order_by(
            CollectorRun.started_at.desc(),
            CollectorRun.id.desc(),
        )
        .limit(limit)
    )

    if trigger is not None:
        statement = statement.where(
            CollectorRun.trigger == trigger,
        )

    if status is not None:
        statement = statement.where(
            CollectorRun.status == status,
        )

    return list(db.scalars(statement))