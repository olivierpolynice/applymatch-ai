import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.session import SessionLocal
from app.services.collector_runs import execute_all_collector_runs
from app.services.offer_importer import ImportResult


logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_MINUTES = 15
MINIMUM_INTERVAL_MINUTES = 1
SCHEDULED_JOB_ID = "applymatch-offer-collection"

TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class CollectorSchedulerSettings:
    enabled: bool
    interval_minutes: int
    run_on_startup: bool

    @classmethod
    def from_environment(
        cls,
    ) -> "CollectorSchedulerSettings":
        return cls(
            enabled=parse_boolean_environment(
                "COLLECTOR_SCHEDULER_ENABLED",
                default=False,
            ),
            interval_minutes=parse_interval_minutes(
                os.getenv("COLLECTOR_INTERVAL_MINUTES")
            ),
            run_on_startup=parse_boolean_environment(
                "COLLECTOR_RUN_ON_STARTUP",
                default=False,
            ),
        )


def parse_boolean_environment(
    variable_name: str,
    *,
    default: bool,
) -> bool:
    raw_value = os.getenv(variable_name)

    if raw_value is None:
        return default

    return raw_value.strip().casefold() in TRUE_VALUES


def parse_interval_minutes(raw_value: str | None) -> int:
    if raw_value is None:
        return DEFAULT_INTERVAL_MINUTES

    try:
        interval = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid COLLECTOR_INTERVAL_MINUTES=%r; using %s.",
            raw_value,
            DEFAULT_INTERVAL_MINUTES,
        )
        return DEFAULT_INTERVAL_MINUTES

    return max(interval, MINIMUM_INTERVAL_MINUTES)


def execute_scheduled_collection() -> ImportResult:
    with SessionLocal() as db:
        return execute_all_collector_runs(
            db,
            trigger="scheduled",
        )


def run_collection_once() -> ImportResult | None:
    try:
        result = execute_scheduled_collection()
    except Exception:
        logger.exception("Unexpected scheduled collection error.")
        return None

    logger.info(
        "Scheduled collection completed: found=%s added=%s "
        "duplicates=%s errors=%s",
        result.found,
        result.added,
        result.duplicates,
        result.errors,
    )
    return result


def start_collector_scheduler(
    settings: CollectorSchedulerSettings | None = None,
) -> AsyncIOScheduler | None:
    scheduler_settings = (
        settings or CollectorSchedulerSettings.from_environment()
    )

    if not scheduler_settings.enabled:
        logger.info("Collector scheduler is disabled.")
        return None

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_collection_once,
        trigger="interval",
        minutes=scheduler_settings.interval_minutes,
        id=SCHEDULED_JOB_ID,
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        next_run_time=(
            datetime.now(timezone.utc)
            if scheduler_settings.run_on_startup
            else datetime.now(timezone.utc)
            + timedelta(
                minutes=scheduler_settings.interval_minutes
            )
        ),
    )
    scheduler.start()
    logger.info(
        "Collector scheduler started: interval=%s minute(s), "
        "run_on_startup=%s",
        scheduler_settings.interval_minutes,
        scheduler_settings.run_on_startup,
    )
    return scheduler


async def stop_collector_scheduler(
    scheduler: AsyncIOScheduler | None,
) -> None:
    if scheduler is None:
        return

    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Collector scheduler stopped.")
