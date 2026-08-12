from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CandidateProfileCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    education_level: str = Field(min_length=1, max_length=100)
    program: str = Field(min_length=1, max_length=200)
    target_contract: str = Field(min_length=1, max_length=100)
    availability: str = Field(min_length=1, max_length=100)
    work_schedule: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=150)
    target_roles: str = Field(min_length=1)
    skills: str = Field(min_length=1)


class CandidateProfileUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    education_level: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    program: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    target_contract: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    availability: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    work_schedule: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    location: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    target_roles: str | None = Field(
        default=None,
        min_length=1,
    )
    skills: str | None = Field(
        default=None,
        min_length=1,
    )


class CandidateProfileRead(CandidateProfileCreate, ORMModel):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


OfferStatus = Literal[
    "new",
    "saved",
    "applied",
    "rejected",
    "archived",
]


class JobOfferCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    company: str = Field(min_length=1, max_length=150)
    location: str = Field(min_length=1, max_length=150)
    contract_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=20)
    source: str = Field(min_length=1, max_length=100)
    source_url: HttpUrl | None = None
    published_at: datetime | None = None


class JobOfferUpdate(BaseModel):
    status: OfferStatus


class JobOfferRead(ORMModel):
    id: int
    title: str
    company: str
    location: str
    contract_type: str
    description: str
    source: str
    source_url: str | None
    status: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MatchDetails(BaseModel):
    skills_score: int
    role_score: int
    contract_score: int
    location_score: int
    education_score: int
    role_match: bool
    contract_match: bool
    location_match: bool
    education_match: bool


class MatchResultRead(ORMModel):
    id: int
    profile_id: int
    offer_id: int
    score: int
    recommendation: str
    confidence: str
    decision: str
    application_priority: str
    actions: list[str]
    matched_skills: list[str]
    skills_to_strengthen: list[str]
    missing_skills: list[str]
    details: MatchDetails
    created_at: datetime
    updated_at: datetime


class CollectorRunRead(BaseModel):
    found: int
    added: int
    duplicates: int
    errors: int


ValidationQueueStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "archived",
]

ValidationDecision = Literal[
    "approved",
    "rejected",
]


class ValidationQueueCreate(BaseModel):
    match_result_id: int = Field(gt=0)


class ValidationQueueDecisionUpdate(BaseModel):
    decision: ValidationDecision
    reviewer_comment: str | None = Field(
        default=None,
        max_length=2000,
    )


class ValidationQueueRead(ORMModel):
    id: int
    profile_id: int
    offer_id: int
    match_result_id: int
    status: ValidationQueueStatus
    priority: str
    reviewer_comment: str | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime