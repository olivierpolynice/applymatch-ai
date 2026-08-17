from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AdminUser
from app.services.admin_users import (
    create_admin_user,
)
from app.services.security import (
    create_access_token,
)


ADMIN_EMAIL = "admin@applymatch.test"
ADMIN_PASSWORD = "MotDePasse-Test-2026!"
JWT_TEST_SECRET = (
    "applymatch-test-secret-key-"
    "with-at-least-32-characters"
)


@pytest.fixture(autouse=True)
def configure_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        JWT_TEST_SECRET,
    )
    monkeypatch.setenv(
        "JWT_ACCESS_TOKEN_MINUTES",
        "30",
    )


@pytest.fixture
def admin_user(
    db_session: Session,
) -> AdminUser:
    return create_admin_user(
        db_session,
        email=ADMIN_EMAIL,
        password=ADMIN_PASSWORD,
    )


def login_admin(
    client: TestClient,
) -> str:
    response = client.post(
        "/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    assert isinstance(body["access_token"], str)
    assert body["access_token"]

    return body["access_token"]


def test_login_returns_access_token(
    client: TestClient,
    admin_user: AdminUser,
) -> None:
    token = login_admin(client)

    assert token.count(".") == 2


def test_login_rejects_invalid_password(
    client: TestClient,
    admin_user: AdminUser,
) -> None:
    response = client.post(
        "/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": "MotDePasse-Incorrect!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password",
    }


def test_me_rejects_missing_token(
    client: TestClient,
) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required",
    }


def test_me_returns_authenticated_admin(
    client: TestClient,
    admin_user: AdminUser,
) -> None:
    token = login_admin(client)

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == admin_user.id
    assert response.json()["email"] == ADMIN_EMAIL
    assert response.json()["is_active"] is True
    assert "hashed_password" not in response.json()


def test_me_rejects_invalid_token(
    client: TestClient,
) -> None:
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required",
    }


def test_me_rejects_expired_token(
    client: TestClient,
    admin_user: AdminUser,
) -> None:
    token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required",
    }


def test_me_rejects_inactive_admin(
    client: TestClient,
    db_session: Session,
    admin_user: AdminUser,
) -> None:
    token = login_admin(client)

    admin_user.is_active = False
    db_session.commit()

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required",
    }