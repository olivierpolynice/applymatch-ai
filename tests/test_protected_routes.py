from typing import Any

import pytest
from fastapi.testclient import TestClient


PROTECTED_ROUTES: list[
    tuple[str, str, dict[str, Any] | None]
] = [
    (
        "POST",
        "/collectors/la-bonne-alternance/run",
        None,
    ),
    (
        "GET",
        "/validation-queue",
        None,
    ),
    (
        "POST",
        "/validation-queue",
        {"match_result_id": 1},
    ),
    (
        "GET",
        "/validation-queue/1",
        None,
    ),
    (
        "PATCH",
        "/validation-queue/1/decision",
        {
            "decision": "approved",
            "reviewer_comment": "Test",
        },
    ),
    (
        "GET",
        "/application-drafts",
        None,
    ),
    (
        "POST",
        "/application-drafts",
        {"validation_queue_item_id": 1},
    ),
    (
        "GET",
        "/application-drafts/1",
        None,
    ),
    (
        "PATCH",
        "/application-drafts/1",
        {"status": "reviewed"},
    ),
    (
        "POST",
        "/application-drafts/1/regenerate",
        None,
    ),
    (
        "POST",
        "/job-offers",
        {
            "title": "Offre protégée",
            "company": "Entreprise Test",
            "location": "Paris",
            "contract_type": "Apprentissage",
            "description": "Description de test",
            "source": "Test",
            "source_url": "https://example.com/test",
            "published_at": None,
        },
    ),
    (
        "PATCH",
        "/job-offers/1",
        {"status": "saved"},
    ),
    (
        "DELETE",
        "/job-offers/1",
        None,
    ),
    (
        "GET",
        "/notifications",
        None,
    ),
    (
        "GET",
        "/notifications/unread-count",
        None,
    ),
    (
        "PATCH",
        "/notifications/read-all",
        None,
    ),
    (
        "PATCH",
        "/notifications/1/read",
        None,
    ),
]


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    PROTECTED_ROUTES,
)
def test_sensitive_route_requires_authentication(
    client: TestClient,
    method: str,
    path: str,
    json_body: dict[str, Any] | None,
) -> None:
    response = client.request(
        method,
        path,
        json=json_body,
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required",
    }
    assert response.headers[
        "www-authenticate"
    ] == "Bearer"