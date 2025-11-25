from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class LoginRequest(BaseModel):
    """Request body for login."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    device_info: Optional[str] = Field(None, max_length=500)


class TokenResponse(BaseModel):
    """Response containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Request body for token refresh."""

    refresh_token: str


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str  # user_id as string
    username: str
    exp: int
    type: str


class RoleResponse(BaseSchema):
    """Response for a role."""

    id: UUID
    name: str
    description: Optional[str] = None


class UserRoleResponse(BaseSchema):
    """Response for a user's role assignment."""

    id: UUID
    user_id: UUID
    role_id: UUID
    role: RoleResponse
