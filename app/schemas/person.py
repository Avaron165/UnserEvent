from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr

from app.schemas.base import BaseSchema, AuditMixin


class PersonBase(BaseModel):
    """Base schema for Person."""

    lastname: str = Field(..., min_length=1, max_length=255)
    firstname: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    mobile: Optional[str] = Field(None, max_length=50)


class PersonCreate(PersonBase):
    """Schema for creating a person."""

    pass


class PersonUpdate(BaseModel):
    """Schema for updating a person."""

    lastname: Optional[str] = Field(None, min_length=1, max_length=255)
    firstname: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    mobile: Optional[str] = Field(None, max_length=50)


class PersonResponse(BaseSchema, PersonBase, AuditMixin):
    """Response schema for a person."""

    id: UUID
    is_user: bool


class PersonListResponse(BaseSchema):
    """Response for list of persons."""

    id: UUID
    lastname: str
    firstname: str
    email: Optional[str] = None
    is_user: bool
