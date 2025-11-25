from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_person_manage, require_admin
from app.models.person import Person
from app.models.user import User
from app.schemas.person import (
    PersonCreate,
    PersonUpdate,
    PersonResponse,
    PersonListResponse,
)
from app.schemas.user import UserPromote, UserResponse
from app.services.auth import promote_person_to_user


router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("", response_model=List[PersonListResponse])
async def list_persons(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all persons.
    Optionally filter by search term (searches firstname, lastname, email).
    """
    stmt = select(Person)

    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            (Person.firstname.ilike(search_term))
            | (Person.lastname.ilike(search_term))
            | (Person.email.ilike(search_term))
        )

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    persons = result.scalars().all()

    return [
        PersonListResponse(
            id=p.id,
            lastname=p.lastname,
            firstname=p.firstname,
            email=p.email,
            is_user=p.is_user,
        )
        for p in persons
    ]


@router.post("", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
async def create_person(
    data: PersonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new person.
    """
    person = Person(
        firstname=data.firstname,
        lastname=data.lastname,
        email=data.email,
        mobile=data.mobile,
        created_by_id=current_user.id,
    )
    db.add(person)
    await db.commit()
    await db.refresh(person)

    return PersonResponse(
        id=person.id,
        firstname=person.firstname,
        lastname=person.lastname,
        email=person.email,
        mobile=person.mobile,
        is_user=person.is_user,
        created_at=person.created_at,
        modified_at=person.modified_at,
        created_by_id=person.created_by_id,
        modified_by_id=person.modified_by_id,
    )


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a person by ID.
    """
    stmt = select(Person).where(Person.id == person_id)
    result = await db.execute(stmt)
    person = result.scalar_one_or_none()

    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    return PersonResponse(
        id=person.id,
        firstname=person.firstname,
        lastname=person.lastname,
        email=person.email,
        mobile=person.mobile,
        is_user=person.is_user,
        created_at=person.created_at,
        modified_at=person.modified_at,
        created_by_id=person.created_by_id,
        modified_by_id=person.modified_by_id,
    )


@router.patch("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: UUID,
    data: PersonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_person_manage),
):
    """
    Update a person.
    Requires permission to manage this person.
    """
    stmt = select(Person).where(Person.id == person_id)
    result = await db.execute(stmt)
    person = result.scalar_one_or_none()

    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(person, field, value)

    person.modified_by_id = current_user.id
    await db.commit()
    await db.refresh(person)

    return PersonResponse(
        id=person.id,
        firstname=person.firstname,
        lastname=person.lastname,
        email=person.email,
        mobile=person.mobile,
        is_user=person.is_user,
        created_at=person.created_at,
        modified_at=person.modified_at,
        created_by_id=person.created_by_id,
        modified_by_id=person.modified_by_id,
    )


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
    person_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """
    Delete a person.
    Requires admin permission.
    """
    stmt = select(Person).where(Person.id == person_id)
    result = await db.execute(stmt)
    person = result.scalar_one_or_none()

    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )

    await db.delete(person)
    await db.commit()


@router.post("/{person_id}/promote", response_model=UserResponse)
async def promote_to_user(
    person_id: UUID,
    data: UserPromote,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin()),
):
    """
    Promote a person to a user (add login capability).
    Requires admin permission.
    """
    # Check if username already exists
    stmt = select(User).where(User.username == data.username)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = await promote_person_to_user(
        db,
        person_id=person_id,
        username=data.username,
        password=data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Person not found or already a user",
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        last_login=user.last_login,
        person=user.person,
    )
