from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AdminUser
from app.services.security import (
    InvalidAccessTokenError,
    decode_access_token,
)


bearer_scheme = HTTPBearer(
    auto_error=False,
)


def authentication_required() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def get_current_admin(
    credentials: (
        HTTPAuthorizationCredentials | None
    ) = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AdminUser:
    if (
        credentials is None
        or credentials.scheme.casefold()
        != "bearer"
    ):
        raise authentication_required()

    try:
        payload: dict[str, Any] = (
            decode_access_token(
                credentials.credentials,
            )
        )
        subject = payload.get("sub")
        admin_id = int(subject)
    except (
        InvalidAccessTokenError,
        TypeError,
        ValueError,
    ) as error:
        raise authentication_required() from error

    admin = db.get(
        AdminUser,
        admin_id,
    )

    if admin is None or not admin.is_active:
        raise authentication_required()

    return admin
