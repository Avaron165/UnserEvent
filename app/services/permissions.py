from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.auth import Role, UserRole
from app.models.division import Division, DivisionMember, DivisionRole
from app.models.team import Team, TeamMember, TeamRole


async def has_global_role(
    db: AsyncSession,
    user_id: UUID,
    role_name: str,
) -> bool:
    """Check if user has a specific global role."""
    stmt = (
        select(UserRole)
        .join(Role)
        .where(UserRole.user_id == user_id, Role.name == role_name)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def is_admin(db: AsyncSession, user_id: UUID) -> bool:
    """Check if user is a global admin."""
    return await has_global_role(db, user_id, "admin")


async def is_superuser(db: AsyncSession, user_id: UUID) -> bool:
    """Check if user is a superuser (highest privilege level)."""
    return await has_global_role(db, user_id, "superuser")


async def has_elevated_privileges(db: AsyncSession, user_id: UUID) -> bool:
    """
    Check if user has elevated privileges (superuser or admin).
    Superusers and admins can bypass division/team membership requirements.
    """
    return await is_superuser(db, user_id) or await is_admin(db, user_id)


async def get_division_role(
    db: AsyncSession,
    user_id: UUID,
    division_id: UUID,
) -> Optional[DivisionRole]:
    """Get user's role in a specific division."""
    # First, get the person_id for this user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        return None

    stmt = select(DivisionMember).where(
        DivisionMember.person_id == user_id,
        DivisionMember.division_id == division_id,
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()

    return membership.role if membership else None


async def get_division_ancestors(
    db: AsyncSession,
    division_id: UUID,
) -> list[UUID]:
    """Get all ancestor division IDs (parent, grandparent, etc.)."""
    ancestors = []
    current_id = division_id

    while current_id is not None:
        stmt = select(Division).where(Division.id == current_id)
        result = await db.execute(stmt)
        division = result.scalar_one_or_none()

        if division is None:
            break

        if division.parent_id is not None:
            ancestors.append(division.parent_id)
            current_id = division.parent_id
        else:
            break

    return ancestors


async def can_manage_division(
    db: AsyncSession,
    user_id: UUID,
    division_id: UUID,
) -> bool:
    """
    Check if user can manage a division.
    User can manage if:
    - User is superuser or global admin, OR
    - User is admin of this division, OR
    - User is admin of any ancestor division
    """
    # Superuser or global admin can manage anything
    if await has_elevated_privileges(db, user_id):
        return True

    # Check this division
    role = await get_division_role(db, user_id, division_id)
    if role == DivisionRole.ADMIN:
        return True

    # Check ancestor divisions
    ancestors = await get_division_ancestors(db, division_id)
    for ancestor_id in ancestors:
        role = await get_division_role(db, user_id, ancestor_id)
        if role == DivisionRole.ADMIN:
            return True

    return False


async def can_view_division(
    db: AsyncSession,
    user_id: UUID,
    division_id: UUID,
) -> bool:
    """
    Check if user can view a division.
    User can view if:
    - User is superuser or global admin, OR
    - User has any role in this division, OR
    - User has any role in an ancestor division
    """
    if await has_elevated_privileges(db, user_id):
        return True

    # Check this division
    role = await get_division_role(db, user_id, division_id)
    if role is not None:
        return True

    # Check ancestors
    ancestors = await get_division_ancestors(db, division_id)
    for ancestor_id in ancestors:
        role = await get_division_role(db, user_id, ancestor_id)
        if role is not None:
            return True

    return False


async def get_team_role(
    db: AsyncSession,
    user_id: UUID,
    team_id: UUID,
) -> Optional[TeamRole]:
    """Get user's role in a specific team."""
    stmt = select(TeamMember).where(
        TeamMember.person_id == user_id,
        TeamMember.team_id == team_id,
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()

    return membership.role if membership else None


async def can_manage_team(
    db: AsyncSession,
    user_id: UUID,
    team_id: UUID,
) -> bool:
    """
    Check if user can manage a team.
    User can manage if:
    - User is superuser or global admin, OR
    - User is manager/coach in this team, OR
    - User can manage the team's division
    """
    if await has_elevated_privileges(db, user_id):
        return True

    # Check team role
    team_role = await get_team_role(db, user_id, team_id)
    if team_role in [TeamRole.MANAGER, TeamRole.COACH]:
        return True

    # Check division management
    stmt = select(Team).where(Team.id == team_id)
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if team and team.division_id:
        return await can_manage_division(db, user_id, team.division_id)

    return False


async def can_view_team(
    db: AsyncSession,
    user_id: UUID,
    team_id: UUID,
) -> bool:
    """
    Check if user can view a team.
    User can view if:
    - User is superuser or global admin, OR
    - User has any role in this team, OR
    - User can view the team's division
    """
    if await has_elevated_privileges(db, user_id):
        return True

    # Check team membership
    team_role = await get_team_role(db, user_id, team_id)
    if team_role is not None:
        return True

    # Check division
    stmt = select(Team).where(Team.id == team_id)
    result = await db.execute(stmt)
    team = result.scalar_one_or_none()

    if team and team.division_id:
        return await can_view_division(db, user_id, team.division_id)

    return False


async def can_manage_person(
    db: AsyncSession,
    user_id: UUID,
    person_id: UUID,
) -> bool:
    """
    Check if user can manage a person.
    User can manage if:
    - User is superuser or global admin, OR
    - User is the person themselves, OR
    - User can manage any division/team the person belongs to
    """
    if await has_elevated_privileges(db, user_id):
        return True

    # Can manage self
    if user_id == person_id:
        return True

    # Check if user manages any division the person belongs to
    stmt = select(DivisionMember).where(DivisionMember.person_id == person_id)
    result = await db.execute(stmt)
    division_memberships = result.scalars().all()

    for membership in division_memberships:
        if await can_manage_division(db, user_id, membership.division_id):
            return True

    # Check if user manages any team the person belongs to
    stmt = select(TeamMember).where(TeamMember.person_id == person_id)
    result = await db.execute(stmt)
    team_memberships = result.scalars().all()

    for membership in team_memberships:
        if await can_manage_team(db, user_id, membership.team_id):
            return True

    return False


async def assign_global_role(
    db: AsyncSession,
    user_id: UUID,
    role_name: str,
) -> bool:
    """Assign a global role to a user."""
    # Get role
    stmt = select(Role).where(Role.name == role_name)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()

    if role is None:
        return False

    # Check if already assigned
    if await has_global_role(db, user_id, role_name):
        return True

    # Assign
    user_role = UserRole(user_id=user_id, role_id=role.id)
    db.add(user_role)
    await db.commit()

    return True
