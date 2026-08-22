from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ApplicationArchive, ApplicationDraft, JobOffer
from app.services.notifications import create_notification_once


def build_daily_report(
    db: Session,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    current = now or datetime.now(timezone.utc)
    since = current - timedelta(hours=24)
    collected = db.scalar(
        select(func.count()).select_from(JobOffer).where(JobOffer.created_at >= since)
    ) or 0
    rejected = db.scalar(
        select(func.count()).select_from(JobOffer).where(
            JobOffer.updated_at >= since, JobOffer.status == "rejected"
        )
    ) or 0
    prepared = db.scalar(
        select(func.count()).select_from(ApplicationDraft).where(
            ApplicationDraft.created_at >= since
        )
    ) or 0
    sent = db.scalar(
        select(func.count()).select_from(ApplicationArchive).where(
            ApplicationArchive.sent_at >= since
        )
    ) or 0
    companies = db.scalar(
        select(func.count(func.distinct(ApplicationArchive.company))).where(
            ApplicationArchive.sent_at >= since
        )
    ) or 0
    problems = db.scalar(
        select(func.count()).select_from(JobOffer).where(
            JobOffer.updated_at >= since,
            JobOffer.application_status == "failed",
        )
    ) or 0
    report = {
        "offers_collected": collected,
        "offers_rejected": rejected,
        "applications_prepared": prepared,
        "applications_sent": sent,
        "companies_contacted": companies,
        "problems_to_resolve": problems,
    }
    create_notification_once(
        db,
        notification_type="daily_report",
        level="info",
        title="Rapport quotidien des candidatures",
        message=(
            f"Collectées : {collected} · Rejetées : {rejected} · "
            f"Préparées : {prepared} · Envoyées : {sent} · "
            f"Entreprises : {companies} · Problèmes : {problems}."
        ),
        target_url=(
            f"#applications-history-report-{current.date().isoformat()}"
        ),
    )
    return report
