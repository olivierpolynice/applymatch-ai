import logging
import os
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CollectorRun
from app.services.collectors.la_bonne_alternance import (
    collect_lba_offers,
)
from app.services.collectors.france_travail import (
    collect_france_travail_offers,
)
from app.services.collectors.jooble import (
    collect_jooble_offers,
)
from app.services.collectors.choisir_service_public import (
    collect_choisir_service_public_offers,
)
from app.services.collectors.emploi_territorial import (
    collect_emploi_territorial_offers,
)
from app.services.collectors.greenhouse import (
    collect_greenhouse_offers,
)
from app.services.collectors.lever import collect_lever_offers
from app.services.collectors.smartrecruiters import (
    collect_smartrecruiters_offers,
)
from app.services.match_results import (
    match_new_offers,
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

CollectorName = Literal[
    "la-bonne-alternance",
    "france-travail",
    "jooble",
    "choisir-service-public",
    "emploi-territorial",
    "greenhouse",
    "lever",
    "smartrecruiters",
]

COLLECTOR_LABELS: dict[CollectorName, str] = {
    "la-bonne-alternance": "La Bonne Alternance",
    "france-travail": "France Travail",
    "jooble": "Jooble",
    "choisir-service-public": "Choisir le Service Public",
    "emploi-territorial": "Emploi Territorial",
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "smartrecruiters": "SmartRecruiters",
}

COLLECTOR_ENVIRONMENT: dict[
    CollectorName,
    tuple[str, ...],
] = {
    "la-bonne-alternance": ("LBA_API_KEY",),
    "france-travail": (
        "FRANCE_TRAVAIL_CLIENT_ID",
        "FRANCE_TRAVAIL_CLIENT_SECRET",
    ),
    "jooble": ("JOOBLE_API_KEY",),
    "choisir-service-public": (),
    "emploi-territorial": ("EMPLOI_TERRITORIAL_RSS_URL",),
    "greenhouse": ("GREENHOUSE_BOARDS",),
    "lever": ("LEVER_SITES",),
    "smartrecruiters": ("SMARTRECRUITERS_COMPANIES",),
}


def is_collector_configured(
    collector: CollectorName,
) -> bool:
    return all(
        bool(os.getenv(variable, "").strip())
        for variable in COLLECTOR_ENVIRONMENT[collector]
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_collector_run(
    db: Session,
    *,
    trigger: CollectorTrigger,
    collector: CollectorName = "la-bonne-alternance",
) -> CollectorRun:
    collector_run = CollectorRun(
        collector=collector,
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
    collector: CollectorName = "la-bonne-alternance",
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
                f"par {COLLECTOR_LABELS[collector]}."
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
    collector: CollectorName = "la-bonne-alternance",
) -> None:
    try:
        create_notification(
            db,
            notification_type="system_error",
            level="error",
            title="Échec de la collecte",
            message=(
                f"La collecte {COLLECTOR_LABELS[collector]} "
                f"a échoué : {str(error)[:500]}"
            ),
            target_url="#collector",
        )
    except Exception:
        db.rollback()

        logger.exception(
            "Unable to create collector failure notification."
        )


def run_automatic_matching(
    db: Session,
    *,
    result: ImportResult,
) -> None:
    if not result.added_offer_ids:
        return

    try:
        matching_result = match_new_offers(
            db,
            offer_ids=result.added_offer_ids,
        )
    except Exception:
        db.rollback()

        logger.exception(
            (
                "Automatic matching could not be "
                "started after collection."
            )
        )

        return

    logger.info(
        (
            "Automatic matching completed: "
            "analyzed=%s skipped=%s errors=%s"
        ),
        matching_result.analyzed,
        matching_result.skipped,
        matching_result.errors,
    )


def execute_collector_run(
    db: Session,
    *,
    trigger: CollectorTrigger,
    collector: CollectorName = "la-bonne-alternance",
) -> tuple[CollectorRun, ImportResult]:
    collector_run = create_collector_run(
        db,
        trigger=trigger,
        collector=collector,
    )

    try:
        if collector == "la-bonne-alternance":
            offers = collect_lba_offers()
        elif collector == "france-travail":
            offers = collect_france_travail_offers()
        elif collector == "jooble":
            offers = collect_jooble_offers()
        elif collector == "choisir-service-public":
            offers = collect_choisir_service_public_offers()
        elif collector == "emploi-territorial":
            offers = collect_emploi_territorial_offers()
        elif collector == "greenhouse":
            offers = collect_greenhouse_offers()
        elif collector == "lever":
            offers = collect_lever_offers()
        else:
            offers = collect_smartrecruiters_offers()

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
            collector=collector,
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
        collector=collector,
    )

    run_automatic_matching(
        db,
        result=result,
    )

    return completed_run, result


def combine_import_results(
    results: list[ImportResult],
    *,
    additional_errors: int = 0,
) -> ImportResult:
    return ImportResult(
        found=sum(result.found for result in results),
        added=sum(result.added for result in results),
        duplicates=sum(
            result.duplicates for result in results
        ),
        errors=(
            sum(result.errors for result in results)
            + additional_errors
        ),
        added_offer_ids=tuple(
            offer_id
            for result in results
            for offer_id in result.added_offer_ids
        ),
    )


def execute_all_collector_runs(
    db: Session,
    *,
    trigger: CollectorTrigger,
) -> ImportResult:
    results: list[ImportResult] = []
    failures = 0

    for collector in COLLECTOR_LABELS:
        if not is_collector_configured(collector):
            logger.info(
                "Collector %s skipped: not configured.",
                collector,
            )
            continue

        try:
            _, result = execute_collector_run(
                db,
                trigger=trigger,
                collector=collector,
            )
        except Exception:
            failures += 1
            logger.exception(
                "Collector %s failed independently.",
                collector,
            )
        else:
            results.append(result)

    return combine_import_results(
        results,
        additional_errors=failures,
    )


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
