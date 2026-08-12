from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import CandidateProfile


class ProfileIdentity(BaseModel):
    full_name: str = Field(min_length=1)
    education_level: str = Field(min_length=1)
    current_program: str = Field(min_length=1)


class Availability(BaseModel):
    contract_type: str
    start_date: str
    work_study_schedule: str


class Location(BaseModel):
    preferred: list[str]
    mobility: str


class Preferences(BaseModel):
    manual_application_approval_required: bool = True
    automatic_application_allowed: bool = False
    active: bool = True


class CandidateProfileDocument(BaseModel):
    schema_version: str
    profile: ProfileIdentity
    skills: dict[str, list[str]]
    target_domains: list[str]
    target_roles: list[str]
    location: Location
    availability: Availability
    ats_keywords: list[str]
    preferences: Preferences


def default_profile_path() -> Path:
    return Path(__file__).resolve().parents[2] / "candidate_profile" / "candidate_profile.yaml"


def load_profile(path: Path | None = None) -> CandidateProfileDocument:
    profile_path = path or default_profile_path()
    with profile_path.open(encoding="utf-8") as file:
        raw: Any = yaml.safe_load(file)
    return CandidateProfileDocument.model_validate(raw)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def document_to_database_values(document: CandidateProfileDocument) -> dict[str, Any]:
    all_skills = [
        skill
        for category_skills in document.skills.values()
        for skill in category_skills
    ]
    all_skills.extend(document.ats_keywords)
    location = ", ".join(_unique(document.location.preferred))
    return {
        "full_name": document.profile.full_name,
        "education_level": document.profile.education_level,
        "program": document.profile.current_program,
        "target_contract": document.availability.contract_type,
        "availability": document.availability.start_date,
        "work_schedule": document.availability.work_study_schedule,
        "location": location or document.location.mobility,
        "target_roles": ", ".join(_unique(document.target_roles + document.target_domains)),
        "skills": ", ".join(_unique(all_skills)),
        "is_active": document.preferences.active,
    }


def sync_profile(db: Session, path: Path | None = None) -> CandidateProfile:
    document = load_profile(path)
    values = document_to_database_values(document)

    db.execute(update(CandidateProfile).values(is_active=False))
    profile = db.scalar(
        select(CandidateProfile).where(
            CandidateProfile.full_name == document.profile.full_name
        )
    )
    if profile is None:
        profile = CandidateProfile(**values)
        db.add(profile)
    else:
        for key, value in values.items():
            setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile
