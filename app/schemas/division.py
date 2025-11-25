from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema, AuditMixin
from app.models.division import DivisionRole


class DivisionBase(BaseModel):
    """Base schema for Division."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class DivisionCreate(DivisionBase):
    """Schema for creating a division."""

    parent_id: Optional[UUID] = None


class DivisionUpdate(BaseModel):
    """Schema for updating a division."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None


class DivisionResponse(BaseSchema, DivisionBase, AuditMixin):
    """Response schema for a division."""

    id: UUID
    parent_id: Optional[UUID] = None


class DivisionTreeResponse(BaseSchema, DivisionBase):
    """Response schema for division with hierarchy."""

    id: UUID
    parent_id: Optional[UUID] = None
    sub_divisions: List["DivisionTreeResponse"] = []


# Rebuild model for self-reference
DivisionTreeResponse.model_rebuild()


class DivisionMemberCreate(BaseModel):
    """Schema for adding a member to a division."""

    person_id: UUID
    role: DivisionRole = DivisionRole.MEMBER


class DivisionMemberUpdate(BaseModel):
    """Schema for updating a division member."""

    role: DivisionRole


class DivisionMemberResponse(BaseSchema, AuditMixin):
    """Response schema for a division member."""

    id: UUID
    division_id: UUID
    person_id: UUID
    role: DivisionRole
    person_name: Optional[str] = None


class DivisionListResponse(BaseSchema):
    """Response for list of divisions."""

    id: UUID
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    member_count: int = 0
    team_count: int = 0
