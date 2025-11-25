from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import (
    require_division_manage,
    require_admin,
    DivisionPermission,
)
from app.models.division import Division, DivisionMember, DivisionRole
from app.models.user import User
from app.schemas.division import (
    DivisionCreate,
    DivisionUpdate,
    DivisionResponse,
    DivisionTreeResponse,
    DivisionListResponse,
    DivisionMemberCreate,
    DivisionMemberUpdate,
    DivisionMemberResponse,
)


router = APIRouter(prefix="/divisions", tags=["divisions"])


@router.get("", response_model=List[DivisionListResponse])
async def list_divisions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    parent_id: Optional[UUID] = None,
    root_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List divisions.
    Use root_only=true to get only top-level divisions.
    Use parent_id to get children of a specific division.
    """
    stmt = select(Division).options(
        selectinload(Division.members),
        selectinload(Division.teams),
    )

    if root_only:
        stmt = stmt.where(Division.parent_id.is_(None))
    elif parent_id is not None:
        stmt = stmt.where(Division.parent_id == parent_id)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    divisions = result.scalars().all()

    return [
        DivisionListResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            parent_id=d.parent_id,
            member_count=len(d.members),
            team_count=len(d.teams),
        )
        for d in divisions
    ]


@router.get("/tree", response_model=List[DivisionTreeResponse])
async def get_division_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the complete division hierarchy as a tree.
    """

    async def build_tree(parent_id: Optional[UUID]) -> List[DivisionTreeResponse]:
        stmt = select(Division).where(Division.parent_id == parent_id)
        result = await db.execute(stmt)
        divisions = result.scalars().all()

        tree = []
        for d in divisions:
            children = await build_tree(d.id)
            tree.append(
                DivisionTreeResponse(
                    id=d.id,
                    name=d.name,
                    description=d.description,
                    parent_id=d.parent_id,
                    sub_divisions=children,
                )
            )
        return tree

    return await build_tree(None)


@router.post("", response_model=DivisionResponse, status_code=status.HTTP_201_CREATED)
async def create_division(
    data: DivisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new division.
    If parent_id is set, requires permission to manage parent division.
    Otherwise requires admin permission.
    """
    # Check permissions
    if data.parent_id is not None:
        # Check if parent exists and user can manage it
        stmt = select(Division).where(Division.id == data.parent_id)
        result = await db.execute(stmt)
        parent = result.scalar_one_or_none()

        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent division not found",
            )

        # Permission check via dependency would be cleaner, but for flexibility:
        from app.services.permissions import can_manage_division

        if not await can_manage_division(db, current_user.id, data.parent_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to create sub-division",
            )
    else:
        # Creating root division requires admin
        from app.services.permissions import is_admin

        if not await is_admin(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required to create root division",
            )

    division = Division(
        name=data.name,
        description=data.description,
        parent_id=data.parent_id,
        created_by_id=current_user.id,
    )
    db.add(division)
    await db.commit()
    await db.refresh(division)

    return DivisionResponse(
        id=division.id,
        name=division.name,
        description=division.description,
        parent_id=division.parent_id,
        created_at=division.created_at,
        modified_at=division.modified_at,
        created_by_id=division.created_by_id,
        modified_by_id=division.modified_by_id,
    )


@router.get("/{division_id}", response_model=DivisionResponse)
async def get_division(
    division_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a division by ID.
    """
    stmt = select(Division).where(Division.id == division_id)
    result = await db.execute(stmt)
    division = result.scalar_one_or_none()

    if division is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Division not found",
        )

    return DivisionResponse(
        id=division.id,
        name=division.name,
        description=division.description,
        parent_id=division.parent_id,
        created_at=division.created_at,
        modified_at=division.modified_at,
        created_by_id=division.created_by_id,
        modified_by_id=division.modified_by_id,
    )


@router.patch("/{division_id}", response_model=DivisionResponse)
async def update_division(
    division_id: UUID,
    data: DivisionUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(DivisionPermission("manage")),
    current_user: User = Depends(get_current_user),
):
    """
    Update a division.
    Requires permission to manage this division.
    """
    stmt = select(Division).where(Division.id == division_id)
    result = await db.execute(stmt)
    division = result.scalar_one_or_none()

    if division is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Division not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(division, field, value)

    division.modified_by_id = current_user.id
    await db.commit()
    await db.refresh(division)

    return DivisionResponse(
        id=division.id,
        name=division.name,
        description=division.description,
        parent_id=division.parent_id,
        created_at=division.created_at,
        modified_at=division.modified_at,
        created_by_id=division.created_by_id,
        modified_by_id=division.modified_by_id,
    )


@router.delete("/{division_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_division(
    division_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(DivisionPermission("manage")),
):
    """
    Delete a division.
    Requires permission to manage this division.
    """
    stmt = select(Division).where(Division.id == division_id)
    result = await db.execute(stmt)
    division = result.scalar_one_or_none()

    if division is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Division not found",
        )

    await db.delete(division)
    await db.commit()


# Division Members
@router.get("/{division_id}/members", response_model=List[DivisionMemberResponse])
async def list_division_members(
    division_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all members of a division.
    """
    stmt = (
        select(DivisionMember)
        .options(selectinload(DivisionMember.person))
        .where(DivisionMember.division_id == division_id)
    )
    result = await db.execute(stmt)
    members = result.scalars().all()

    return [
        DivisionMemberResponse(
            id=m.id,
            division_id=m.division_id,
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
    "/{division_id}/members",
    response_model=DivisionMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_division_member(
    division_id: UUID,
    data: DivisionMemberCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(DivisionPermission("manage")),
    current_user: User = Depends(get_current_user),
):
    """
    Add a member to a division.
    Requires permission to manage this division.
    """
    member = DivisionMember(
        division_id=division_id,
        person_id=data.person_id,
        role=data.role,
        created_by_id=current_user.id,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return DivisionMemberResponse(
        id=member.id,
        division_id=member.division_id,
        person_id=member.person_id,
        role=member.role,
        person_name=None,
        created_at=member.created_at,
        modified_at=member.modified_at,
        created_by_id=member.created_by_id,
        modified_by_id=member.modified_by_id,
    )


@router.delete(
    "/{division_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_division_member(
    division_id: UUID,
    member_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(DivisionPermission("manage")),
):
    """
    Remove a member from a division.
    Requires permission to manage this division.
    """
    stmt = select(DivisionMember).where(
        DivisionMember.id == member_id,
        DivisionMember.division_id == division_id,
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
