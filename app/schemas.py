from datetime import datetime, timezone
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )


class CandidateProfileCreate(BaseModel):
    full_name: str = Field(
        min_length=1,
        max_length=150,
    )
    education_level: str = Field(
        min_length=1,
        max_length=100,
    )
    program: str = Field(
        min_length=1,
        max_length=200,
    )
    target_contract: str = Field(
        min_length=1,
        max_length=100,
    )
    availability: str = Field(
        min_length=1,
        max_length=100,
    )
    work_schedule: str = Field(
        min_length=1,
        max_length=100,
    )
    location: str = Field(
        min_length=1,
        max_length=150,
    )
    target_roles: str = Field(
        min_length=1,
    )
    skills: str = Field(
        min_length=1,
    )
    professional_summary: str | None = Field(
        default=None,
        max_length=3000,
    )
    experience_highlights: str | None = Field(
        default=None,
        max_length=5000,
    )
    project_highlights: str | None = Field(
        default=None,
        max_length=5000,
    )


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
    professional_summary: str | None = Field(
        default=None,
        max_length=3000,
    )
    experience_highlights: str | None = Field(
        default=None,
        max_length=5000,
    )
    project_highlights: str | None = Field(
        default=None,
        max_length=5000,
    )


class CandidateProfileRead(
    CandidateProfileCreate,
    ORMModel,
):
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

ApplicationChannel = Literal[
    "official_api",
    "recruitment_email",
    "authorized_form",
    "manual",
    "unsupported",
]

ApplicationStatus = Literal[
    "not_started",
    "documents_ready",
    "manual_required",
    "pending_confirmation",
    "sent",
    "failed",
]


class JobOfferCreate(BaseModel):
    title: str = Field(
        min_length=2,
        max_length=200,
    )
    company: str = Field(
        min_length=1,
        max_length=150,
    )
    location: str = Field(
        min_length=1,
        max_length=150,
    )
    contract_type: str = Field(
        min_length=1,
        max_length=100,
    )
    description: str = Field(
        min_length=20,
    )
    source: str = Field(
        min_length=1,
        max_length=100,
    )
    external_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    source_url: HttpUrl | None = None
    published_at: datetime | None = None
    expires_at: datetime | None = None
    experience_min: int | None = Field(
        default=None,
        ge=0,
        le=50,
    )
    experience_max: int | None = Field(
        default=None,
        ge=0,
        le=50,
    )
    application_channel: ApplicationChannel | None = None
    application_status: ApplicationStatus = "not_started"
    provider_confirmation_id: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
    )

    @field_validator("published_at", "expires_at")
    @classmethod
    def require_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("La date doit contenir un fuseau horaire")

        return (
            value.astimezone(timezone.utc)
            if value is not None
            else None
        )

    @model_validator(mode="after")
    def validate_ranges(self) -> "JobOfferCreate":
        if (
            self.experience_min is not None
            and self.experience_max is not None
            and self.experience_min > self.experience_max
        ):
            raise ValueError(
                "experience_min ne peut pas dépasser experience_max"
            )

        if (
            self.published_at is not None
            and self.expires_at is not None
            and self.expires_at <= self.published_at
        ):
            raise ValueError(
                "expires_at doit être postérieure à published_at"
            )

        return self


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
    external_id: str | None
    source_url: str | None
    status: str
    published_at: datetime | None
    expires_at: datetime | None
    experience_min: int | None
    experience_max: int | None
    application_channel: str | None
    application_status: str
    provider_confirmation_id: str | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MatchDetails(BaseModel):
    skills_score: int
    role_score: int
    contract_score: int
    location_score: int
    education_score: int
    experience_score: int
    freshness_score: int
    role_match: bool
    contract_match: bool
    location_match: bool
    education_match: bool
    experience_match: bool
    eligibility_reasons: list[str]


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


CollectorTrigger = Literal[
    "manual",
    "scheduled",
]

CollectorRunStatus = Literal[
    "running",
    "completed",
    "failed",
]


class CollectorRunHistoryRead(ORMModel):
    id: int
    collector: str
    trigger: CollectorTrigger
    status: CollectorRunStatus
    found: int
    added: int
    duplicates: int
    errors: int
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


NotificationType = Literal[
    "collector_completed",
    "new_offers",
    "high_score",
    "validation_required",
    "draft_ready",
    "system_error",
]

NotificationLevel = Literal[
    "info",
    "success",
    "warning",
    "error",
]


class NotificationRead(ORMModel):
    id: int
    notification_type: NotificationType
    level: NotificationLevel
    title: str
    message: str
    target_url: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationUnreadCountRead(BaseModel):
    unread_count: int


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
    match_result_id: int = Field(
        gt=0,
    )


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


ApplicationDraftStatus = Literal[
    "draft",
    "reviewed",
    "archived",
]


class ApplicationDraftCreate(BaseModel):
    validation_queue_item_id: int = Field(
        gt=0,
    )


class ApplicationDraftUpdate(BaseModel):
    cover_letter: str | None = Field(
        default=None,
        min_length=50,
        max_length=10000,
    )
    short_message: str | None = Field(
        default=None,
        min_length=20,
        max_length=2000,
    )
    cv_adaptation_tips: str | None = Field(
        default=None,
        min_length=20,
        max_length=5000,
    )
    status: ApplicationDraftStatus | None = None


class ApplicationDraftRead(ORMModel):
    id: int
    validation_queue_item_id: int
    profile_id: int
    offer_id: int
    status: ApplicationDraftStatus
    version: int
    cover_letter: str
    short_message: str
    cv_adaptation_tips: str
    adapted_cv_snapshot: str
    proposed_answers: list[dict[str, str]]
    generated_at: datetime
    created_at: datetime
    updated_at: datetime


AutomationChannel = Literal[
    "official_api",
    "recruitment_email",
    "authorized_form",
    "unsupported",
]


class AutomationEvaluationCreate(BaseModel):
    draft_id: int = Field(gt=0)
    channel: AutomationChannel
    channel_authorized: bool = False
    has_unknown_questions: bool = False


class AutomationEvaluationRead(BaseModel):
    mode: Literal["automatic", "manual_approval"]
    eligible: bool
    reasons: list[str]


class ConfirmApplicationSentCreate(AutomationEvaluationCreate):
    provider_confirmation_id: str = Field(min_length=3, max_length=255)
    application_mode: Literal["automatic", "manual"] = "automatic"


class ApplicationArchiveRead(ORMModel):
    id: int
    draft_id: int
    profile_id: int
    offer_id: int
    company: str
    offer_title: str
    application_mode: str
    channel: str
    provider_confirmation_id: str
    cv_snapshot: str
    cover_letter_snapshot: str
    short_message_snapshot: str
    proposed_answers_snapshot: list[dict[str, str]]
    sent_at: datetime
    archived_at: datetime
