from typing import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.services.permissions import (
    is_admin,
    is_superuser,
    has_elevated_privileges,
    has_global_role,
    can_manage_division,
    can_view_division,
    can_manage_team,
    can_view_team,
    can_manage_person,
)


def require_admin():
    """Dependency that requires the user to be a global admin."""

    async def _require_admin(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if not await is_admin(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return current_user

    return _require_admin


def require_superuser():
    """Dependency that requires the user to be a superuser."""

    async def _require_superuser(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if not await is_superuser(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superuser access required",
            )
        return current_user

    return _require_superuser


def require_elevated_privileges():
    """Dependency that requires the user to be a superuser or admin."""

    async def _require_elevated(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if not await has_elevated_privileges(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or superuser access required",
            )
        return current_user

    return _require_elevated


def require_role(role_name: str):
    """Dependency factory that requires a specific global role."""

    async def _require_role(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if not await has_global_role(db, current_user.id, role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_name}' required",
            )
        return current_user

    return _require_role


class DivisionPermission:
    """Permission checker for division operations."""

    def __init__(self, action: str = "view"):
        self.action = action

    async def __call__(
        self,
        division_id: UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if self.action == "manage":
            allowed = await can_manage_division(db, current_user.id, division_id)
        else:
            allowed = await can_view_division(db, current_user.id, division_id)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No permission to {self.action} this division",
            )
        return current_user


class TeamPermission:
    """Permission checker for team operations."""

    def __init__(self, action: str = "view"):
        self.action = action

    async def __call__(
        self,
        team_id: UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if self.action == "manage":
            allowed = await can_manage_team(db, current_user.id, team_id)
        else:
            allowed = await can_view_team(db, current_user.id, team_id)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No permission to {self.action} this team",
            )
        return current_user


class PersonPermission:
    """Permission checker for person operations."""

    def __init__(self, action: str = "view"):
        self.action = action

    async def __call__(
        self,
        person_id: UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if self.action == "manage":
            allowed = await can_manage_person(db, current_user.id, person_id)
        else:
            # For now, any authenticated user can view persons
            # You might want to restrict this based on division/team membership
            allowed = True

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No permission to {self.action} this person",
            )
        return current_user


# Pre-configured permission instances
require_division_view = DivisionPermission("view")
require_division_manage = DivisionPermission("manage")
require_team_view = TeamPermission("view")
require_team_manage = TeamPermission("manage")
require_person_manage = PersonPermission("manage")
