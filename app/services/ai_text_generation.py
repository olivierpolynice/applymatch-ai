import json
import logging
import os
import re
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models import CandidateProfile, JobOffer, MatchResult
from app.services.profile_loader import load_profile
from app.services.technology_matcher import normalize


logger = logging.getLogger(__name__)

TRUE_VALUES = {"1", "true", "yes", "on"}


class GeneratedApplicationTexts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cover_letter: str = Field(min_length=200, max_length=10000)
    short_message: str = Field(min_length=40, max_length=2000)


def generation_is_enabled() -> bool:
    return (
        os.getenv("AI_TEXT_GENERATION_ENABLED", "false")
        .strip()
        .casefold()
        in TRUE_VALUES
    )


def extract_json_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("AI response does not contain choices")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("AI response content is empty")

    return content


def count_term(text: str, term: str) -> int:
    normalized_text = normalize(text)
    normalized_term = normalize(term)
    return len(
        re.findall(
            rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])",
            normalized_text,
        )
    )


def validate_no_new_unknown_technology(
    *,
    generated_text: str,
    fallback_text: str,
    unknown_technologies: list[str],
) -> None:
    for technology in unknown_technologies:
        if count_term(generated_text, technology) > count_term(
            fallback_text,
            technology,
        ):
            raise ValueError(
                f"AI introduced an unverified technology: {technology}"
            )


def build_generation_payload(
    *,
    profile: CandidateProfile,
    offer: JobOffer,
    match_result: MatchResult,
    fallback_cover_letter: str,
    fallback_short_message: str,
) -> dict[str, Any]:
    yaml_profile = load_profile()
    verified_names = list(match_result.known_technologies)
    evidence = {
        technology.name: technology.evidence
        for technology in yaml_profile.technologies
        if technology.name in verified_names
    }
    authorized_projects = list(
        dict.fromkeys(
            project
            for projects in evidence.values()
            for project in projects
        )
    )

    return {
        "offer": {
            "title": offer.title,
            "company": offer.company,
            "location": offer.location,
            "contract_type": offer.contract_type,
            "description": offer.description,
        },
        "candidate": {
            "full_name": yaml_profile.profile.full_name,
            "education_level": yaml_profile.profile.education_level,
            "program": yaml_profile.profile.current_program,
            "availability": yaml_profile.availability.start_date,
            "schedule": yaml_profile.availability.work_study_schedule,
            "target_roles": yaml_profile.target_roles,
        },
        "authorized_projects": authorized_projects,
        "known_technologies": verified_names,
        "technology_evidence": evidence,
        "letter_template": fallback_cover_letter,
        "message_template": fallback_short_message,
    }


def enhance_application_texts(
    *,
    profile: CandidateProfile,
    offer: JobOffer,
    match_result: MatchResult,
    fallback_cover_letter: str,
    fallback_short_message: str,
    client: httpx.Client | None = None,
) -> tuple[str, str]:
    if not generation_is_enabled():
        return fallback_cover_letter, fallback_short_message

    api_url = os.getenv("AI_API_URL", "").strip()
    api_key = os.getenv("AI_API_KEY", "").strip()
    model = os.getenv("AI_MODEL", "").strip()

    if not api_url or not api_key or not model:
        logger.warning("AI generation is enabled but not configured.")
        return fallback_cover_letter, fallback_short_message

    allowed_context = build_generation_payload(
        profile=profile,
        offer=offer,
        match_result=match_result,
        fallback_cover_letter=fallback_cover_letter,
        fallback_short_message=fallback_short_message,
    )
    http_client = client or httpx.Client(timeout=45.0)
    owns_client = client is None

    try:
        response = http_client.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Réécris uniquement la lettre et le message. "
                            "N'invente aucune compétence, expérience, "
                            "formation ou projet. Ne calcule et ne modifie "
                            "aucun score. Réponds en JSON strict avec les "
                            "clés cover_letter et short_message."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            allowed_context,
                            ensure_ascii=False,
                        ),
                    },
                ],
            },
        )
        response.raise_for_status()
        generated = GeneratedApplicationTexts.model_validate_json(
            extract_json_content(response.json())
        )
        combined_generated = (
            generated.cover_letter + "\n" + generated.short_message
        )
        combined_fallback = (
            fallback_cover_letter + "\n" + fallback_short_message
        )
        validate_no_new_unknown_technology(
            generated_text=combined_generated,
            fallback_text=combined_fallback,
            unknown_technologies=list(
                match_result.unknown_technologies
            ),
        )
        return generated.cover_letter, generated.short_message
    except (httpx.HTTPError, ValueError, ValidationError):
        logger.exception(
            "AI text generation failed; deterministic templates retained."
        )
        return fallback_cover_letter, fallback_short_message
    finally:
        if owns_client:
            http_client.close()
