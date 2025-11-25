from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema, AuditMixin
from app.models.team import TeamRole


class TeamBase(BaseModel):
    """Base schema for Team."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    """Schema for creating a team."""

    division_id: Optional[UUID] = None
    external_org: Optional[str] = Field(None, max_length=255)
    responsible_id: Optional[UUID] = None  # NULL = proxy team


class ProxyTeamCreate(BaseModel):
    """Schema for creating a proxy team (external team)."""

    name: str = Field(..., min_length=1, max_length=255)
    external_org: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TeamPromote(BaseModel):
    """Schema for promoting a proxy team to full team."""

    responsible_id: UUID
    division_id: Optional[UUID] = None


class TeamUpdate(BaseModel):
    """Schema for updating a team."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    division_id: Optional[UUID] = None
    responsible_id: Optional[UUID] = None


class TeamResponse(BaseSchema, TeamBase, AuditMixin):
    """Response schema for a team."""

    id: UUID
    division_id: Optional[UUID] = None
    external_org: Optional[str] = None
    responsible_id: Optional[UUID] = None
    promoted_at: Optional[datetime] = None
    is_proxy: bool
    is_external: bool


class TeamDetailResponse(TeamResponse):
    """Detailed response for a team with members."""

    responsible_name: Optional[str] = None
    division_name: Optional[str] = None
    member_count: int = 0


class TeamListResponse(BaseSchema):
    """Response for list of teams."""

    id: UUID
    name: str
    division_id: Optional[UUID] = None
    division_name: Optional[str] = None
    external_org: Optional[str] = None
    is_proxy: bool
    member_count: int = 0


class TeamMemberCreate(BaseModel):
    """Schema for adding a member to a team."""

    person_id: UUID
    role: TeamRole = TeamRole.PLAYER


class TeamMemberUpdate(BaseModel):
    """Schema for updating a team member."""

    role: TeamRole


class TeamMemberResponse(BaseSchema, AuditMixin):
    """Response schema for a team member."""

    id: UUID
    team_id: UUID
    person_id: UUID
    role: TeamRole
    person_name: Optional[str] = None
