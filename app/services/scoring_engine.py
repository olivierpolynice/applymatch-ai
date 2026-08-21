from typing import Literal

from pydantic import BaseModel, Field


DOCUMENT_PREPARATION_THRESHOLD = 60

ScoreDecision = Literal[
    "rejected",
    "manual_review",
    "documents_ready",
]


class ScoreExplanation(BaseModel):
    total_score: int = Field(ge=0, le=100)
    known_skills: list[str] = Field(default_factory=list)
    unknown_skills: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    decision: ScoreDecision


def decide_score(
    total_score: int,
    blocking_reasons: list[str],
) -> ScoreDecision:
    if blocking_reasons:
        return "rejected"

    if total_score >= DOCUMENT_PREPARATION_THRESHOLD:
        return "documents_ready"

    return "manual_review"


def explain_score(
    *,
    total_score: int,
    known_skills: list[str],
    unknown_skills: list[str],
    blocking_reasons: list[str],
) -> ScoreExplanation:
    return ScoreExplanation(
        total_score=total_score,
        known_skills=list(dict.fromkeys(known_skills)),
        unknown_skills=list(dict.fromkeys(unknown_skills)),
        blocking_reasons=list(dict.fromkeys(blocking_reasons)),
        decision=decide_score(total_score, blocking_reasons),
    )
