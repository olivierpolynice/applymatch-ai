import os

from celery import Celery
from celery.schedules import crontab


broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "applymatch",
    broker=broker,
    backend=backend,
    include=["app.background.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=86400,
    task_track_started=True,
    beat_schedule={
        "collect-offers-every-15-minutes": {
            "task": "applymatch.collect_offers",
            "schedule": 900.0,
        },
        "daily-application-report": {
            "task": "applymatch.daily_report",
            "schedule": crontab(hour=18, minute=0),
        },
    },
)
