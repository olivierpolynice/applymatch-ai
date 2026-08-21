from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (  # noqa: F401
    AdminUser,
    CandidateProfile,
)
from app.services.admin_users import (
    create_admin_user,
)


TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"
TEST_ADMIN_EMAIL = "admin@applymatch.test"
TEST_ADMIN_PASSWORD = "MotDePasse-Test-2026!"
TEST_JWT_SECRET = (
    "applymatch-test-secret-key-"
    "with-at-least-32-characters"
)


@pytest.fixture(autouse=True)
def disable_external_automation_during_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLLECTOR_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("COLLECTOR_RUN_ON_STARTUP", "false")
    monkeypatch.setenv("AI_TEXT_GENERATION_ENABLED", "false")

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=test_engine)

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(
    db_session: Session,
) -> Generator[TestClient, None, None]:
    def override_get_db() -> (
        Generator[Session, None, None]
    ):
        yield db_session

    app.dependency_overrides[get_db] = (
        override_get_db
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        TEST_JWT_SECRET,
    )
    monkeypatch.setenv(
        "JWT_ACCESS_TOKEN_MINUTES",
        "30",
    )

    create_admin_user(
        db_session,
        email=TEST_ADMIN_EMAIL,
        password=TEST_ADMIN_PASSWORD,
    )

    login_response = client.post(
        "/auth/login",
        json={
            "email": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASSWORD,
        },
    )

    if login_response.status_code != 200:
        raise RuntimeError(
            "Unable to authenticate the test client"
        )

    access_token = login_response.json()[
        "access_token"
    ]
    client.headers.update(
        {
            "Authorization": (
                f"Bearer {access_token}"
            ),
        }
    )

    yield client
