from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CandidateProfile
from app.services.profile_loader import (
    load_profile,
    sync_profile,
)


PROFILE_PATH = (
    Path(__file__).resolve().parents[1]
    / "candidate_profile"
    / "candidate_profile.yaml"
)


def test_yaml_profile_is_valid() -> None:
    document = load_profile(PROFILE_PATH)

    assert (
        document.profile.full_name
        == "Olivier Polynice"
    )
    assert (
        document.availability.contract_type
        == "Alternance ou stage"
    )
    assert (
        document.preferences
        .automatic_application_allowed
        is True
    )
    assert (
        document.preferences
        .manual_application_approval_required
        is True
    )


def test_yaml_sync_keeps_one_active_profile(
    db_session: Session,
) -> None:
    old_profile = CandidateProfile(
        full_name="Ancien profil",
        education_level="Bac+5",
        program="Ancien programme",
        target_contract="Alternance",
        availability="2026-09",
        work_schedule="4 jours en entreprise",
        location="Paris",
        target_roles="Cloud",
        skills="Python",
        is_active=True,
    )
    db_session.add(old_profile)
    db_session.commit()

    first_sync = sync_profile(
        db_session,
        PROFILE_PATH,
    )
    second_sync = sync_profile(
        db_session,
        PROFILE_PATH,
    )

    assert first_sync.id == second_sync.id
    assert (
        second_sync.full_name
        == "Olivier Polynice"
    )
    assert second_sync.is_active is True
    assert old_profile.is_active is False

    active_count = db_session.scalar(
        select(func.count())
        .select_from(CandidateProfile)
        .where(
            CandidateProfile.is_active.is_(
                True
            )
        )
    )

    assert active_count == 1