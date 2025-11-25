from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr

from app.schemas.base import BaseSchema
from app.schemas.person import PersonResponse


class UserBase(BaseModel):
    """Base schema for User."""

    username: str = Field(..., min_length=3, max_length=100)


class UserCreate(BaseModel):
    """Schema for creating a user (with new person)."""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    lastname: str = Field(..., min_length=1, max_length=255)
    firstname: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    mobile: Optional[str] = Field(None, max_length=50)


class UserPromote(BaseModel):
    """Schema for promoting a person to user."""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    username: Optional[str] = Field(None, min_length=3, max_length=100)
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    """Schema for changing password."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseSchema):
    """Response schema for a user."""

    id: UUID
    username: str
    is_active: bool
    last_login: Optional[datetime] = None
    person: PersonResponse


class UserListResponse(BaseSchema):
    """Response for list of users."""

    id: UUID
    username: str
    is_active: bool
    last_login: Optional[datetime] = None
    full_name: str
    email: Optional[str] = None


class CurrentUserResponse(UserResponse):
    """Response for current authenticated user with roles."""

    roles: list[str] = []
