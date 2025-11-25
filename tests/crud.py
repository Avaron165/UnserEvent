"""
CRUD utility functions for testing.
These functions directly interact with SQLAlchemy models without going through the API.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.person import Person
from app.models.user import User
from app.models.division import Division, DivisionMember, DivisionRole
from app.models.team import Team, TeamMember, TeamRole
from app.models.auth import Role, UserRole, RefreshToken
from app.services.auth import hash_password


# ============================================================================
# PERSON CRUD
# ============================================================================

async def create_person(
    db: AsyncSession,
    *,
    firstname: str,
    lastname: str,
    email: Optional[str] = None,
    mobile: Optional[str] = None,
    created_by_id: Optional[UUID] = None,
) -> Person:
    """Create a new person."""
    person = Person(
        firstname=firstname,
        lastname=lastname,
        email=email,
        mobile=mobile,
        created_by_id=created_by_id,
    )
    db.add(person)
    await db.flush()
    await db.refresh(person)
    return person


async def get_person(db: AsyncSession, person_id: UUID) -> Optional[Person]:
    """Get a person by ID."""
    stmt = select(Person).where(Person.id == person_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_person_by_email(db: AsyncSession, email: str) -> Optional[Person]:
    """Get a person by email."""
    stmt = select(Person).where(Person.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_person(
    db: AsyncSession,
    person_id: UUID,
    *,
    firstname: Optional[str] = None,
    lastname: Optional[str] = None,
    email: Optional[str] = None,
    mobile: Optional[str] = None,
    modified_by_id: Optional[UUID] = None,
) -> Optional[Person]:
    """Update an existing person."""
    person = await get_person(db, person_id)
    if person is None:
        return None

    if firstname is not None:
        person.firstname = firstname
    if lastname is not None:
        person.lastname = lastname
    if email is not None:
        person.email = email
    if mobile is not None:
        person.mobile = mobile
    if modified_by_id is not None:
        person.modified_by_id = modified_by_id

    await db.flush()
    await db.refresh(person)
    return person


async def delete_person(db: AsyncSession, person_id: UUID) -> bool:
    """Delete a person by ID."""
    person = await get_person(db, person_id)
    if person is None:
        return False
    await db.delete(person)
    await db.flush()
    return True


async def list_persons(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Person]:
    """List all persons."""
    stmt = select(Person).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# USER CRUD
# ============================================================================

async def create_user(
    db: AsyncSession,
    *,
    firstname: str,
    lastname: str,
    username: str,
    password: str,
    email: Optional[str] = None,
    mobile: Optional[str] = None,
    is_active: bool = True,
) -> User:
    """Create a new user with associated person."""
    # Create person first
    person = Person(
        firstname=firstname,
        lastname=lastname,
        email=email,
        mobile=mobile,
    )
    db.add(person)
    await db.flush()

    # Create user with same ID
    user = User(
        id=person.id,
        username=username,
        password_hash=hash_password(password),
        is_active=is_active,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_user_for_person(
    db: AsyncSession,
    person_id: UUID,
    *,
    username: str,
    password: str,
    is_active: bool = True,
) -> Optional[User]:
    """Promote an existing person to a user."""
    person = await get_person(db, person_id)
    if person is None:
        return None

    # Check if already a user
    stmt = select(User).where(User.id == person_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        return None  # Already a user

    user = User(
        id=person_id,
        username=username,
        password_hash=hash_password(password),
        is_active=is_active,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get a user by ID."""
    stmt = select(User).options(selectinload(User.person)).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get a user by username."""
    stmt = select(User).options(selectinload(User.person)).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    username: Optional[str] = None,
    password: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[User]:
    """Update an existing user."""
    user = await get_user(db, user_id)
    if user is None:
        return None

    if username is not None:
        user.username = username
    if password is not None:
        user.password_hash = hash_password(password)
    if is_active is not None:
        user.is_active = is_active

    await db.flush()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: UUID) -> bool:
    """Delete a user (but keep the person)."""
    user = await get_user(db, user_id)
    if user is None:
        return False
    await db.delete(user)
    await db.flush()
    return True


async def list_users(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    """List all users."""
    stmt = select(User).options(selectinload(User.person)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# DIVISION CRUD
# ============================================================================

async def create_division(
    db: AsyncSession,
    *,
    name: str,
    description: Optional[str] = None,
    parent_id: Optional[UUID] = None,
    created_by_id: Optional[UUID] = None,
) -> Division:
    """Create a new division."""
    division = Division(
        name=name,
        description=description,
        parent_id=parent_id,
        created_by_id=created_by_id,
    )
    db.add(division)
    await db.flush()
    await db.refresh(division)
    return division


async def get_division(db: AsyncSession, division_id: UUID) -> Optional[Division]:
    """Get a division by ID."""
    stmt = select(Division).where(Division.id == division_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_division_with_children(db: AsyncSession, division_id: UUID) -> Optional[Division]:
    """Get a division with its sub-divisions loaded."""
    stmt = (
        select(Division)
        .options(selectinload(Division.sub_divisions))
        .where(Division.id == division_id)
        .execution_options(populate_existing=True)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_division(
    db: AsyncSession,
    division_id: UUID,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    parent_id: Optional[UUID] = None,
    modified_by_id: Optional[UUID] = None,
) -> Optional[Division]:
    """Update an existing division."""
    division = await get_division(db, division_id)
    if division is None:
        return None

    if name is not None:
        division.name = name
    if description is not None:
        division.description = description
    if parent_id is not None:
        division.parent_id = parent_id
    if modified_by_id is not None:
        division.modified_by_id = modified_by_id

    await db.flush()
    await db.refresh(division)
    return division


async def delete_division(db: AsyncSession, division_id: UUID) -> bool:
    """Delete a division by ID."""
    division = await get_division(db, division_id)
    if division is None:
        return False
    await db.delete(division)
    await db.flush()
    return True


async def list_divisions(
    db: AsyncSession,
    *,
    parent_id: Optional[UUID] = None,
    root_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[Division]:
    """List divisions."""
    stmt = select(Division)
    if root_only:
        stmt = stmt.where(Division.parent_id.is_(None))
    elif parent_id is not None:
        stmt = stmt.where(Division.parent_id == parent_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# DIVISION MEMBER CRUD
# ============================================================================

async def add_division_member(
    db: AsyncSession,
    *,
    division_id: UUID,
    person_id: UUID,
    role: DivisionRole = DivisionRole.MEMBER,
    created_by_id: Optional[UUID] = None,
) -> DivisionMember:
    """Add a member to a division."""
    member = DivisionMember(
        division_id=division_id,
        person_id=person_id,
        role=role,
        created_by_id=created_by_id,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def get_division_member(
    db: AsyncSession,
    member_id: UUID,
) -> Optional[DivisionMember]:
    """Get a division member by ID."""
    stmt = select(DivisionMember).where(DivisionMember.id == member_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_division_membership(
    db: AsyncSession,
    division_id: UUID,
    person_id: UUID,
) -> Optional[DivisionMember]:
    """Get a specific division membership."""
    stmt = select(DivisionMember).where(
        DivisionMember.division_id == division_id,
        DivisionMember.person_id == person_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_division_member(
    db: AsyncSession,
    member_id: UUID,
    *,
    role: Optional[DivisionRole] = None,
    modified_by_id: Optional[UUID] = None,
) -> Optional[DivisionMember]:
    """Update a division member's role."""
    member = await get_division_member(db, member_id)
    if member is None:
        return None

    if role is not None:
        member.role = role
    if modified_by_id is not None:
        member.modified_by_id = modified_by_id

    await db.flush()
    await db.refresh(member)
    return member


async def delete_division_member(db: AsyncSession, member_id: UUID) -> bool:
    """Remove a member from a division."""
    member = await get_division_member(db, member_id)
    if member is None:
        return False
    await db.delete(member)
    await db.flush()
    return True


async def list_division_members(
    db: AsyncSession,
    division_id: UUID,
) -> list[DivisionMember]:
    """List all members of a division."""
    stmt = (
        select(DivisionMember)
        .options(selectinload(DivisionMember.person))
        .where(DivisionMember.division_id == division_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# TEAM CRUD
# ============================================================================

async def create_team(
    db: AsyncSession,
    *,
    name: str,
    description: Optional[str] = None,
    division_id: Optional[UUID] = None,
    responsible_id: Optional[UUID] = None,
    external_org: Optional[str] = None,
    created_by_id: Optional[UUID] = None,
) -> Team:
    """Create a new team."""
    team = Team(
        name=name,
        description=description,
        division_id=division_id,
        responsible_id=responsible_id,
        external_org=external_org,
        created_by_id=created_by_id,
    )
    # If responsible is set, it's not a proxy
    if responsible_id is not None:
        team.promoted_at = datetime.now(timezone.utc)

    db.add(team)
    await db.flush()
    await db.refresh(team)
    return team


async def create_proxy_team(
    db: AsyncSession,
    *,
    name: str,
    external_org: str,
    description: Optional[str] = None,
    created_by_id: Optional[UUID] = None,
) -> Team:
    """Create a proxy team (external team placeholder)."""
    team = Team(
        name=name,
        description=description,
        external_org=external_org,
        division_id=None,
        responsible_id=None,
        created_by_id=created_by_id,
    )
    db.add(team)
    await db.flush()
    await db.refresh(team)
    return team


async def get_team(db: AsyncSession, team_id: UUID) -> Optional[Team]:
    """Get a team by ID."""
    stmt = select(Team).where(Team.id == team_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_team_with_members(db: AsyncSession, team_id: UUID) -> Optional[Team]:
    """Get a team with its members loaded."""
    stmt = (
        select(Team)
        .options(
            selectinload(Team.members).selectinload(TeamMember.person),
            selectinload(Team.responsible),
            selectinload(Team.division),
        )
        .where(Team.id == team_id)
        .execution_options(populate_existing=True)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_team(
    db: AsyncSession,
    team_id: UUID,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    division_id: Optional[UUID] = None,
    responsible_id: Optional[UUID] = None,
    modified_by_id: Optional[UUID] = None,
) -> Optional[Team]:
    """Update an existing team."""
    team = await get_team(db, team_id)
    if team is None:
        return None

    if name is not None:
        team.name = name
    if description is not None:
        team.description = description
    if division_id is not None:
        team.division_id = division_id
    if responsible_id is not None:
        team.responsible_id = responsible_id
    if modified_by_id is not None:
        team.modified_by_id = modified_by_id

    await db.flush()
    await db.refresh(team)
    return team


async def promote_team(
    db: AsyncSession,
    team_id: UUID,
    *,
    responsible_id: UUID,
    division_id: Optional[UUID] = None,
    modified_by_id: Optional[UUID] = None,
) -> Optional[Team]:
    """Promote a proxy team to a full team."""
    team = await get_team(db, team_id)
    if team is None:
        return None

    if not team.is_proxy:
        return None  # Already promoted

    team.responsible_id = responsible_id
    team.division_id = division_id
    team.promoted_at = datetime.now(timezone.utc)
    if modified_by_id is not None:
        team.modified_by_id = modified_by_id

    await db.flush()
    await db.refresh(team)
    return team


async def delete_team(db: AsyncSession, team_id: UUID) -> bool:
    """Delete a team by ID."""
    team = await get_team(db, team_id)
    if team is None:
        return False
    await db.delete(team)
    await db.flush()
    return True


async def list_teams(
    db: AsyncSession,
    *,
    division_id: Optional[UUID] = None,
    proxy_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[Team]:
    """List teams."""
    stmt = select(Team)
    if division_id is not None:
        stmt = stmt.where(Team.division_id == division_id)
    if proxy_only:
        stmt = stmt.where(Team.responsible_id.is_(None))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# TEAM MEMBER CRUD
# ============================================================================

async def add_team_member(
    db: AsyncSession,
    *,
    team_id: UUID,
    person_id: UUID,
    role: TeamRole = TeamRole.PLAYER,
    created_by_id: Optional[UUID] = None,
) -> TeamMember:
    """Add a member to a team."""
    member = TeamMember(
        team_id=team_id,
        person_id=person_id,
        role=role,
        created_by_id=created_by_id,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def get_team_member(db: AsyncSession, member_id: UUID) -> Optional[TeamMember]:
    """Get a team member by ID."""
    stmt = select(TeamMember).where(TeamMember.id == member_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_team_membership(
    db: AsyncSession,
    team_id: UUID,
    person_id: UUID,
) -> Optional[TeamMember]:
    """Get a specific team membership."""
    stmt = select(TeamMember).where(
        TeamMember.team_id == team_id,
        TeamMember.person_id == person_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_team_member(
    db: AsyncSession,
    member_id: UUID,
    *,
    role: Optional[TeamRole] = None,
    modified_by_id: Optional[UUID] = None,
) -> Optional[TeamMember]:
    """Update a team member's role."""
    member = await get_team_member(db, member_id)
    if member is None:
        return None

    if role is not None:
        member.role = role
    if modified_by_id is not None:
        member.modified_by_id = modified_by_id

    await db.flush()
    await db.refresh(member)
    return member


async def delete_team_member(db: AsyncSession, member_id: UUID) -> bool:
    """Remove a member from a team."""
    member = await get_team_member(db, member_id)
    if member is None:
        return False
    await db.delete(member)
    await db.flush()
    return True


async def list_team_members(
    db: AsyncSession,
    team_id: UUID,
) -> list[TeamMember]:
    """List all members of a team."""
    stmt = (
        select(TeamMember)
        .options(selectinload(TeamMember.person))
        .where(TeamMember.team_id == team_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ============================================================================
# ROLE CRUD
# ============================================================================

async def get_role_by_name(db: AsyncSession, name: str) -> Optional[Role]:
    """Get a role by name."""
    stmt = select(Role).where(Role.name == name)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_role(db: AsyncSession, name: str, description: str = "") -> Role:
    """Get a role by name or create it if it doesn't exist."""
    role = await get_role_by_name(db, name)
    if role is None:
        role = Role(name=name, description=description)
        db.add(role)
        await db.flush()
        await db.refresh(role)
    return role


async def assign_role_to_user(
    db: AsyncSession,
    user_id: UUID,
    role_name: str,
) -> Optional[UserRole]:
    """Assign a global role to a user."""
    role = await get_role_by_name(db, role_name)
    if role is None:
        return None

    # Check if already assigned
    stmt = select(UserRole).where(
        UserRole.user_id == user_id,
        UserRole.role_id == role.id,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    user_role = UserRole(user_id=user_id, role_id=role.id)
    db.add(user_role)
    await db.flush()
    await db.refresh(user_role)
    return user_role


async def remove_role_from_user(
    db: AsyncSession,
    user_id: UUID,
    role_name: str,
) -> bool:
    """Remove a global role from a user."""
    role = await get_role_by_name(db, role_name)
    if role is None:
        return False

    stmt = select(UserRole).where(
        UserRole.user_id == user_id,
        UserRole.role_id == role.id,
    )
    result = await db.execute(stmt)
    user_role = result.scalar_one_or_none()

    if user_role is None:
        return False

    await db.delete(user_role)
    await db.flush()
    return True


async def list_user_roles(db: AsyncSession, user_id: UUID) -> list[str]:
    """List all roles assigned to a user."""
    stmt = (
        select(UserRole)
        .options(selectinload(UserRole.role))
        .where(UserRole.user_id == user_id)
    )
    result = await db.execute(stmt)
    user_roles = result.scalars().all()
    return [ur.role.name for ur in user_roles]


# ============================================================================
# CLEANUP UTILITIES
# ============================================================================

async def delete_all_team_members(db: AsyncSession) -> int:
    """Delete all team members."""
    stmt = delete(TeamMember)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount


async def delete_all_teams(db: AsyncSession) -> int:
    """Delete all teams."""
    stmt = delete(Team)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount


async def delete_all_division_members(db: AsyncSession) -> int:
    """Delete all division members."""
    stmt = delete(DivisionMember)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount


async def delete_all_divisions(db: AsyncSession) -> int:
    """Delete all divisions."""
    stmt = delete(Division)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount


async def delete_all_user_roles(db: AsyncSession) -> int:
    """Delete all user role assignments."""
    stmt = delete(UserRole)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount


async def delete_all_refresh_tokens(db: AsyncSession) -> int:
    """Delete all refresh tokens."""
    stmt = delete(RefreshToken)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount


async def delete_all_users(db: AsyncSession) -> int:
    """Delete all users (but keep persons)."""
    stmt = delete(User)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount


async def delete_all_persons(db: AsyncSession) -> int:
    """Delete all persons."""
    stmt = delete(Person)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount


async def cleanup_all(db: AsyncSession) -> dict[str, int]:
    """Delete all data from all tables (in correct order)."""
    counts = {}
    counts["refresh_tokens"] = await delete_all_refresh_tokens(db)
    counts["user_roles"] = await delete_all_user_roles(db)
    counts["team_members"] = await delete_all_team_members(db)
    counts["teams"] = await delete_all_teams(db)
    counts["division_members"] = await delete_all_division_members(db)
    counts["divisions"] = await delete_all_divisions(db)
    counts["users"] = await delete_all_users(db)
    counts["persons"] = await delete_all_persons(db)
    return counts
