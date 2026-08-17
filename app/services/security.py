import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash


load_dotenv()

JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_MINUTES = 30

password_hash = PasswordHash.recommended()


class AuthenticationConfigurationError(RuntimeError):
    pass


class InvalidAccessTokenError(RuntimeError):
    pass


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "").strip()

    if len(secret) < 32:
        raise AuthenticationConfigurationError(
            "JWT_SECRET_KEY must contain at least 32 characters"
        )

    return secret


def get_access_token_minutes() -> int:
    raw_value = os.getenv(
        "JWT_ACCESS_TOKEN_MINUTES",
        str(DEFAULT_ACCESS_TOKEN_MINUTES),
    )

    try:
        minutes = int(raw_value)
    except ValueError as error:
        raise AuthenticationConfigurationError(
            "JWT_ACCESS_TOKEN_MINUTES must be an integer"
        ) from error

    if minutes < 1:
        raise AuthenticationConfigurationError(
            "JWT_ACCESS_TOKEN_MINUTES must be at least 1"
        )

    return minutes


def create_access_token(
    *,
    user_id: int,
    email: str,
    expires_delta: timedelta | None = None,
) -> str:
    issued_at = datetime.now(timezone.utc)

    expires_at = issued_at + (
        expires_delta
        or timedelta(
            minutes=get_access_token_minutes(),
        )
    )

    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "iat": issued_at,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(
    token: str,
) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            options={
                "require": [
                    "sub",
                    "type",
                    "iat",
                    "exp",
                ],
            },
        )
    except jwt.PyJWTError as error:
        raise InvalidAccessTokenError(
            "Invalid or expired access token"
        ) from error

    if payload.get("type") != "access":
        raise InvalidAccessTokenError(
            "Invalid access token type"
        )

    return payload