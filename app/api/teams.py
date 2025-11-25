from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import TeamPermission, DivisionPermission
from app.models.team import Team, TeamMember, TeamRole
from app.models.division import Division
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    ProxyTeamCreate,
    TeamPromote,
    TeamUpdate,
    TeamResponse,
    TeamDetailResponse,
    TeamListResponse,
    TeamMemberCreate,
    TeamMemberUpdate,
    TeamMemberResponse,
)
from app.services.permissions import can_manage_division, is_admin


router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=List[TeamListResponse])
async def list_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    division_id: Optional[UUID] = None,
    proxy_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List teams.
    Use division_id to filter by division.
    Use proxy_only=true to get only proxy teams.
    """
    stmt = select(Team).options(
        selectinload(Team.division),
        selectinload(Team.members),
    )

    if division_id is not None:
        stmt = stmt.where(Team.division_id == division_id)

    if proxy_only:
        stmt = stmt.where(Team.responsible_id.is_(None))

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    teams = result.scalars().all()

    return [
        TeamListResponse(
            id=t.id,
            name=t.name,
            division_id=t.division_id,
            division_name=t.division.name if t.division else None,
            external_org=t.external_org,
            is_proxy=t.is_proxy,
            member_count=len(t.members),
        )
        for t in teams
    ]


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    data: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new team.
    If division_id is set, requires permission to manage that division.
    """
    # Check division permissions
    if data.division_id is not None:
        if not await can_manage_division(db, current_user.id, data.division_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to create team in this division",
            )

    team = Team(
        name=data.name,
        description=data.description,
        division_id=data.division_id,
        external_org=data.external_org,
        responsible_id=data.responsible_id,
        created_by_id=current_user.id,
    )

    # If responsible is set, it's not a proxy team
    if data.responsible_id:
        team.promoted_at = datetime.now(timezone.utc)

    db.add(team)
    await db.commit()
    await db.refresh(team)

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        division_id=team.division_id,
        external_org=team.external_org,
        responsible_id=team.responsible_id,
        promoted_at=team.promoted_at,
        is_proxy=team.is_proxy,
        is_external=team.is_external,
        created_at=team.created_at,
        modified_at=team.modified_at,
        created_by_id=team.created_by_id,
        modified_by_id=team.modified_by_id,
    )


@router.post("/proxy", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_proxy_team(
    data: ProxyTeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a proxy team (external team placeholder).
    """
    team = Team(
        name=data.name,
        description=data.description,
        external_org=data.external_org,
        division_id=None,
        responsible_id=None,
        created_by_id=current_user.id,
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        division_id=team.division_id,
        external_org=team.external_org,
        responsible_id=team.responsible_id,
        promoted_at=team.promoted_at,
        is_proxy=team.is_proxy,
        is_external=team.is_external,
        created_at=team.created_at,
        modified_at=team.modified_at,
        created_by_id=team.created_by_id,
        modified_by_id=team.modified_by_id,
    )


@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a team by ID.
    """
    stmt = (
        select(Team)
        .options(
            selectinload(Team.division),
            selectinload(Team.responsible),
            selectinload(Team.members),
        )
        .where(Team.id == team_id)
    )
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    return TeamDetailResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        division_id=team.division_id,
        division_name=team.division.name if team.division else None,
        external_org=team.external_org,
        responsible_id=team.responsible_id,
        responsible_name=team.responsible.full_name if team.responsible else None,
        promoted_at=team.promoted_at,
        is_proxy=team.is_proxy,
        is_external=team.is_external,
        member_count=len(team.members),
        created_at=team.created_at,
        modified_at=team.modified_at,
        created_by_id=team.created_by_id,
        modified_by_id=team.modified_by_id,
    )


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: UUID,
    data: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(TeamPermission("manage")),
    current_user: User = Depends(get_current_user),
):
    """
    Update a team.
    Requires permission to manage this team.
    """
    stmt = select(Team).where(Team.id == team_id)
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)

    team.modified_by_id = current_user.id
    await db.commit()
    await db.refresh(team)

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        division_id=team.division_id,
        external_org=team.external_org,
        responsible_id=team.responsible_id,
        promoted_at=team.promoted_at,
        is_proxy=team.is_proxy,
        is_external=team.is_external,
        created_at=team.created_at,
        modified_at=team.modified_at,
        created_by_id=team.created_by_id,
        modified_by_id=team.modified_by_id,
    )


@router.post("/{team_id}/promote", response_model=TeamResponse)
async def promote_team(
    team_id: UUID,
    data: TeamPromote,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Promote a proxy team to a full team.
    Sets the responsible person and optionally assigns to a division.
    """
    stmt = select(Team).where(Team.id == team_id)
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    if not team.is_proxy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team is already a full team",
        )

    # Check division permissions if assigning to division
    if data.division_id is not None:
        if not await can_manage_division(db, current_user.id, data.division_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to assign team to this division",
            )

    team.responsible_id = data.responsible_id
    team.division_id = data.division_id
    team.promoted_at = datetime.now(timezone.utc)
    team.modified_by_id = current_user.id

    await db.commit()
    await db.refresh(team)

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        division_id=team.division_id,
        external_org=team.external_org,
        responsible_id=team.responsible_id,
        promoted_at=team.promoted_at,
        is_proxy=team.is_proxy,
        is_external=team.is_external,
        created_at=team.created_at,
        modified_at=team.modified_at,
        created_by_id=team.created_by_id,
        modified_by_id=team.modified_by_id,
    )


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(TeamPermission("manage")),
):
    """
    Delete a team.
    Requires permission to manage this team.
    """
    stmt = select(Team).where(Team.id == team_id)
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    await db.delete(team)
    await db.commit()


# Team Members
@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
async def list_team_members(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all members of a team.
    """
    stmt = (
        select(TeamMember)
        .options(selectinload(TeamMember.person))
        .where(TeamMember.team_id == team_id)
    )
    result = await db.execute(stmt)
    members = result.scalars().all()

    return [
        TeamMemberResponse(
            id=m.id,
            team_id=m.team_id,
            person_id=m.person_id,
            role=m.role,
            person_name=m.person.full_name if m.person else None,
            created_at=m.created_at,
            modified_at=m.modified_at,
            created_by_id=m.created_by_id,
            modified_by_id=m.modified_by_id,
        )
        for m in members
    ]


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_team_member(
    team_id: UUID,
    data: TeamMemberCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(TeamPermission("manage")),
    current_user: User = Depends(get_current_user),
):
    """
    Add a member to a team.
    Requires permission to manage this team.
    """
    # Check if team exists and is not a proxy
    stmt = select(Team).where(Team.id == team_id)
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    if team.is_proxy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add members to a proxy team",
        )

    member = TeamMember(
        team_id=team_id,
        person_id=data.person_id,
        role=data.role,
        created_by_id=current_user.id,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return TeamMemberResponse(
        id=member.id,
        team_id=member.team_id,
        person_id=member.person_id,
        role=member.role,
        person_name=None,
        created_at=member.created_at,
        modified_at=member.modified_at,
        created_by_id=member.created_by_id,
        modified_by_id=member.modified_by_id,
    )


@router.patch("/{team_id}/members/{member_id}", response_model=TeamMemberResponse)
async def update_team_member(
    team_id: UUID,
    member_id: UUID,
    data: TeamMemberUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(TeamPermission("manage")),
    current_user: User = Depends(get_current_user),
):
    """
    Update a team member's role.
    Requires permission to manage this team.
    """
    stmt = (
        select(TeamMember)
        .options(selectinload(TeamMember.person))
        .where(TeamMember.id == member_id, TeamMember.team_id == team_id)
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    member.role = data.role
    member.modified_by_id = current_user.id
    await db.commit()
    await db.refresh(member)

    return TeamMemberResponse(
        id=member.id,
        team_id=member.team_id,
        person_id=member.person_id,
        role=member.role,
        person_name=member.person.full_name if member.person else None,
        created_at=member.created_at,
        modified_at=member.modified_at,
        created_by_id=member.created_by_id,
        modified_by_id=member.modified_by_id,
    )


@router.delete("/{team_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: UUID,
    member_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(TeamPermission("manage")),
):
    """
    Remove a member from a team.
    Requires permission to manage this team.
    """
    stmt = select(TeamMember).where(
        TeamMember.id == member_id,
        TeamMember.team_id == team_id,
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    await db.delete(member)
    await db.commit()
