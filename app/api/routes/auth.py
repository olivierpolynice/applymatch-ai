from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.api.auth_dependencies import (
    get_current_admin,
)
from app.api.auth_schemas import (
    AdminUserRead,
    LoginRequest,
    TokenResponse,
)
from app.db.session import get_db
from app.models import AdminUser
from app.services.admin_users import (
    authenticate_admin,
)
from app.services.security import (
    create_access_token,
    get_access_token_minutes,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    admin = authenticate_admin(
        db,
        email=data.email,
        password=data.password,
    )

    if admin is None:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    access_token = create_access_token(
        user_id=admin.id,
        email=admin.email,
    )
    expires_in = (
        get_access_token_minutes() * 60
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
    )


@router.get(
    "/me",
    response_model=AdminUserRead,
)
def read_current_admin(
    admin: AdminUser = Depends(
        get_current_admin,
    ),
) -> AdminUser:
    return admin
