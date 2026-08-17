from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=320,
    )
    password: str = Field(
        min_length=1,
        max_length=1024,
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminUserRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    email: str
    is_active: bool
    created_at: datetime
