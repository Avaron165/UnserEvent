"""
Tests for Person CRUD operations.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.person import Person
from tests.crud import (
    create_person,
    get_person,
    get_person_by_email,
    update_person,
    delete_person,
    list_persons,
)


class TestPersonCreate:
    """Tests for creating persons."""

    async def test_create_person_minimal(self, db: AsyncSession):
        """Test creating a person with minimal required fields."""
        person = await create_person(
            db,
            firstname="John",
            lastname="Doe",
        )
        await db.commit()

        assert person.id is not None
        assert person.firstname == "John"
        assert person.lastname == "Doe"
        assert person.email is None
        assert person.mobile is None
        assert person.created_at is not None
        assert person.is_user is False

    async def test_create_person_full(self, db: AsyncSession):
        """Test creating a person with all fields."""
        person = await create_person(
            db,
            firstname="Jane",
            lastname="Doe",
            email="jane.doe@example.com",
            mobile="+49123456789",
        )
        await db.commit()

        assert person.firstname == "Jane"
        assert person.lastname == "Doe"
        assert person.email == "jane.doe@example.com"
        assert person.mobile == "+49123456789"

    async def test_create_multiple_persons(self, db: AsyncSession):
        """Test creating multiple persons."""
        person1 = await create_person(db, firstname="Alice", lastname="Smith")
        person2 = await create_person(db, firstname="Bob", lastname="Smith")
        await db.commit()

        assert person1.id != person2.id
        assert person1.lastname == person2.lastname

    async def test_person_full_name(self, db: AsyncSession):
        """Test the full_name property."""
        person = await create_person(db, firstname="Max", lastname="Mustermann")
        await db.commit()

        assert person.full_name == "Max Mustermann"


class TestPersonRead:
    """Tests for reading persons."""

    async def test_get_person_by_id(self, db: AsyncSession):
        """Test getting a person by ID."""
        created = await create_person(db, firstname="Test", lastname="Person")
        await db.commit()

        fetched = await get_person(db, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.firstname == "Test"

    async def test_get_person_not_found(self, db: AsyncSession):
        """Test getting a non-existent person."""
        from uuid import uuid4

        person = await get_person(db, uuid4())

        assert person is None

    async def test_get_person_by_email(self, db: AsyncSession):
        """Test getting a person by email."""
        from uuid import uuid4
        unique_email = f"test-{uuid4()}@example.com"

        await create_person(
            db,
            firstname="Email",
            lastname="Test",
            email=unique_email,
        )
        await db.commit()

        person = await get_person_by_email(db, unique_email)

        assert person is not None
        assert person.firstname == "Email"

    async def test_list_persons(self, db: AsyncSession):
        """Test listing persons."""
        await create_person(db, firstname="List1", lastname="Test")
        await create_person(db, firstname="List2", lastname="Test")
        await create_person(db, firstname="List3", lastname="Test")
        await db.commit()

        persons = await list_persons(db)

        # Note: There might be other persons from other tests
        assert len(persons) >= 3
        names = [p.firstname for p in persons]
        assert "List1" in names
        assert "List2" in names
        assert "List3" in names

    async def test_list_persons_with_pagination(self, db: AsyncSession):
        """Test listing persons with pagination."""
        for i in range(5):
            await create_person(db, firstname=f"Page{i}", lastname="Test")
        await db.commit()

        page1 = await list_persons(db, skip=0, limit=2)
        page2 = await list_persons(db, skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id


class TestPersonUpdate:
    """Tests for updating persons."""

    async def test_update_person_firstname(self, db: AsyncSession):
        """Test updating a person's firstname."""
        person = await create_person(db, firstname="Original", lastname="Name")
        await db.commit()

        updated = await update_person(db, person.id, firstname="Updated")
        await db.commit()

        assert updated is not None
        assert updated.firstname == "Updated"
        assert updated.lastname == "Name"

    async def test_update_person_multiple_fields(self, db: AsyncSession):
        """Test updating multiple fields at once."""
        person = await create_person(
            db,
            firstname="Old",
            lastname="Name",
            email="old@example.com",
        )
        await db.commit()

        updated = await update_person(
            db,
            person.id,
            firstname="New",
            lastname="Person",
            email="new@example.com",
            mobile="+49999999999",
        )
        await db.commit()

        assert updated.firstname == "New"
        assert updated.lastname == "Person"
        assert updated.email == "new@example.com"
        assert updated.mobile == "+49999999999"

    async def test_update_person_not_found(self, db: AsyncSession):
        """Test updating a non-existent person."""
        from uuid import uuid4

        result = await update_person(db, uuid4(), firstname="Test")

        assert result is None


class TestPersonDelete:
    """Tests for deleting persons."""

    async def test_delete_person(self, db: AsyncSession):
        """Test deleting a person."""
        person = await create_person(db, firstname="ToDelete", lastname="Person")
        await db.commit()
        person_id = person.id

        result = await delete_person(db, person_id)
        await db.commit()

        assert result is True

        # Verify deleted
        fetched = await get_person(db, person_id)
        assert fetched is None

    async def test_delete_person_not_found(self, db: AsyncSession):
        """Test deleting a non-existent person."""
        from uuid import uuid4

        result = await delete_person(db, uuid4())

        assert result is False
