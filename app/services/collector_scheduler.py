import asyncio
import logging
import os
from dataclasses import dataclass

from app.db.session import SessionLocal
from app.services.collector_runs import (
    execute_collector_run,
)
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
)
from app.services.offer_importer import ImportResult


logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_MINUTES = 240
MINIMUM_INTERVAL_MINUTES = 1

TRUE_VALUES = {
    "1",
    "true",
    "yes",
    "on",
}


@dataclass(frozen=True)
class CollectorSchedulerSettings:
    enabled: bool
    interval_minutes: int
    run_on_startup: bool

    @classmethod
    def from_environment(
        cls,
    ) -> "CollectorSchedulerSettings":
        enabled = parse_boolean_environment(
            "COLLECTOR_SCHEDULER_ENABLED",
            default=False,
        )
        run_on_startup = parse_boolean_environment(
            "COLLECTOR_RUN_ON_STARTUP",
            default=False,
        )
        interval_minutes = parse_interval_minutes(
            os.getenv(
                "COLLECTOR_INTERVAL_MINUTES"
            ),
        )

        return cls(
            enabled=enabled,
            interval_minutes=interval_minutes,
            run_on_startup=run_on_startup,
        )

    @property
    def interval_seconds(self) -> float:
        return float(
            self.interval_minutes * 60
        )


def parse_boolean_environment(
    variable_name: str,
    *,
    default: bool,
) -> bool:
    raw_value = os.getenv(variable_name)

    if raw_value is None:
        return default

    return (
        raw_value.strip().casefold()
        in TRUE_VALUES
    )


def parse_interval_minutes(
    raw_value: str | None,
) -> int:
    if raw_value is None:
        return DEFAULT_INTERVAL_MINUTES

    try:
        interval = int(raw_value)
    except ValueError:
        logger.warning(
            (
                "Invalid "
                "COLLECTOR_INTERVAL_MINUTES=%r. "
                "Using the default value: "
                "%s minutes."
            ),
            raw_value,
            DEFAULT_INTERVAL_MINUTES,
        )

        return DEFAULT_INTERVAL_MINUTES

    if interval < MINIMUM_INTERVAL_MINUTES:
        logger.warning(
            (
                "COLLECTOR_INTERVAL_MINUTES "
                "must be at least %s. "
                "Using %s minute."
            ),
            MINIMUM_INTERVAL_MINUTES,
            MINIMUM_INTERVAL_MINUTES,
        )

        return MINIMUM_INTERVAL_MINUTES

    return interval


def execute_scheduled_collection() -> ImportResult:
    with SessionLocal() as db:
        _, result = execute_collector_run(
            db,
            trigger="scheduled",
        )

    return result


async def run_collection_once() -> ImportResult | None:
    try:
        result = await asyncio.to_thread(
            execute_scheduled_collection,
        )
    except CollectorConfigurationError:
        logger.error(
            (
                "Scheduled collection skipped: "
                "LBA_API_KEY is not configured."
            )
        )

        return None
    except CollectorAPIError:
        logger.exception(
            (
                "Scheduled collection failed: "
                "La Bonne Alternance API "
                "is unavailable."
            )
        )

        return None
    except Exception:
        logger.exception(
            (
                "Unexpected scheduled "
                "collection error."
            )
        )

        return None

    logger.info(
        (
            "Scheduled collection completed: "
            "found=%s added=%s "
            "duplicates=%s errors=%s"
        ),
        result.found,
        result.added,
        result.duplicates,
        result.errors,
    )

    return result


async def collector_scheduler_loop(
    settings: CollectorSchedulerSettings,
) -> None:
    logger.info(
        (
            "Collector scheduler started: "
            "interval=%s minute(s), "
            "run_on_startup=%s"
        ),
        settings.interval_minutes,
        settings.run_on_startup,
    )

    if settings.run_on_startup:
        await run_collection_once()

    while True:
        await asyncio.sleep(
            settings.interval_seconds,
        )

        await run_collection_once()


def start_collector_scheduler(
    settings: (
        CollectorSchedulerSettings | None
    ) = None,
) -> asyncio.Task[None] | None:
    scheduler_settings = (
        settings
        or CollectorSchedulerSettings
        .from_environment()
    )

    if not scheduler_settings.enabled:
        logger.info(
            "Collector scheduler is disabled."
        )

        return None

    return asyncio.create_task(
        collector_scheduler_loop(
            scheduler_settings,
        ),
        name=(
            "la-bonne-alternance-"
            "scheduler"
        ),
    )


async def stop_collector_scheduler(
    task: asyncio.Task[None] | None,
) -> None:
    if task is None:
        return

    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        logger.info(
            "Collector scheduler stopped."
        )