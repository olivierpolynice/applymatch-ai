import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Notification
from app.observability import JsonFormatter
from app.services.daily_report import build_daily_report


def test_json_logging_contains_structured_business_fields() -> None:
    record = logging.LogRecord(
        name="applymatch.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="offer_filter_evaluated",
        args=(),
        exc_info=None,
    )
    record.event = "offer_filter_evaluated"
    record.source = "france-travail"
    record.eligible = True

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "offer_filter_evaluated"
    assert payload["source"] == "france-travail"
    assert payload["eligible"] is True
    assert "timestamp" in payload


def test_daily_report_is_complete_and_idempotent(db_session: Session) -> None:
    now = datetime(2026, 8, 21, 18, 0, tzinfo=timezone.utc)

    first = build_daily_report(db_session, now=now)
    second = build_daily_report(db_session, now=now)

    assert first == second == {
        "offers_collected": 0,
        "offers_rejected": 0,
        "applications_prepared": 0,
        "applications_sent": 0,
        "companies_contacted": 0,
        "problems_to_resolve": 0,
    }
    reports = db_session.query(Notification).filter_by(
        notification_type="daily_report"
    ).all()
    assert len(reports) == 1
