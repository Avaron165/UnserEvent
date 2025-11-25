"""
Tests for Division CRUD operations.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.division import Division, DivisionRole
from tests.crud import (
    create_division,
    get_division,
    get_division_with_children,
    update_division,
    delete_division,
    list_divisions,
    add_division_member,
    get_division_member,
    get_division_membership,
    update_division_member,
    delete_division_member,
    list_division_members,
    create_person,
)


class TestDivisionCreate:
    """Tests for creating divisions."""

    async def test_create_division_minimal(self, db: AsyncSession):
        """Test creating a division with minimal required fields."""
        division = await create_division(db, name="Test Division")
        await db.commit()

        assert division.id is not None
        assert division.name == "Test Division"
        assert division.description is None
        assert division.parent_id is None
        assert division.created_at is not None

    async def test_create_division_with_description(self, db: AsyncSession):
        """Test creating a division with description."""
        division = await create_division(
            db,
            name="Full Division",
            description="A detailed description",
        )
        await db.commit()

        assert division.name == "Full Division"
        assert division.description == "A detailed description"

    async def test_create_division_hierarchy(self, db: AsyncSession):
        """Test creating a division hierarchy."""
        parent = await create_division(db, name="Parent Division")
        await db.flush()

        child = await create_division(
            db,
            name="Child Division",
            parent_id=parent.id,
        )
        await db.commit()

        assert child.parent_id == parent.id

        # Verify relationship
        parent_with_children = await get_division_with_children(db, parent.id)
        assert len(parent_with_children.sub_divisions) == 1
        assert parent_with_children.sub_divisions[0].id == child.id

    async def test_create_deep_hierarchy(self, db: AsyncSession):
        """Test creating a deep division hierarchy."""
        root = await create_division(db, name="Root")
        await db.flush()

        level1 = await create_division(db, name="Level 1", parent_id=root.id)
        await db.flush()

        level2 = await create_division(db, name="Level 2", parent_id=level1.id)
        await db.flush()

        level3 = await create_division(db, name="Level 3", parent_id=level2.id)
        await db.commit()

        assert level3.parent_id == level2.id
        assert level2.parent_id == level1.id
        assert level1.parent_id == root.id


class TestDivisionRead:
    """Tests for reading divisions."""

    async def test_get_division_by_id(self, db: AsyncSession):
        """Test getting a division by ID."""
        created = await create_division(db, name="Fetch Test")
        await db.commit()

        fetched = await get_division(db, created.id)

        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_division_not_found(self, db: AsyncSession):
        """Test getting a non-existent division."""
        from uuid import uuid4

        division = await get_division(db, uuid4())

        assert division is None

    async def test_list_root_divisions(self, db: AsyncSession):
        """Test listing only root divisions."""
        root1 = await create_division(db, name="Root 1")
        root2 = await create_division(db, name="Root 2")
        await db.flush()

        child = await create_division(db, name="Child", parent_id=root1.id)
        await db.commit()

        roots = await list_divisions(db, root_only=True)

        root_ids = [d.id for d in roots]
        assert root1.id in root_ids
        assert root2.id in root_ids
        assert child.id not in root_ids

    async def test_list_children_of_division(self, db: AsyncSession):
        """Test listing children of a specific division."""
        parent = await create_division(db, name="Parent")
        await db.flush()

        child1 = await create_division(db, name="Child 1", parent_id=parent.id)
        child2 = await create_division(db, name="Child 2", parent_id=parent.id)
        await db.commit()

        children = await list_divisions(db, parent_id=parent.id)

        child_ids = [d.id for d in children]
        assert len(children) == 2
        assert child1.id in child_ids
        assert child2.id in child_ids


class TestDivisionUpdate:
    """Tests for updating divisions."""

    async def test_update_division_name(self, db: AsyncSession):
        """Test updating a division's name."""
        division = await create_division(db, name="Original")
        await db.commit()

        updated = await update_division(db, division.id, name="Updated")
        await db.commit()

        assert updated.name == "Updated"

    async def test_update_division_parent(self, db: AsyncSession):
        """Test moving a division to a different parent."""
        parent1 = await create_division(db, name="Parent 1")
        parent2 = await create_division(db, name="Parent 2")
        await db.flush()

        child = await create_division(db, name="Child", parent_id=parent1.id)
        await db.commit()

        # Move child to parent2
        updated = await update_division(db, child.id, parent_id=parent2.id)
        await db.commit()

        assert updated.parent_id == parent2.id


class TestDivisionDelete:
    """Tests for deleting divisions."""

    async def test_delete_division(self, db: AsyncSession):
        """Test deleting a division."""
        division = await create_division(db, name="ToDelete")
        await db.commit()
        division_id = division.id

        result = await delete_division(db, division_id)
        await db.commit()

        assert result is True
        assert await get_division(db, division_id) is None

    async def test_delete_division_not_found(self, db: AsyncSession):
        """Test deleting a non-existent division."""
        from uuid import uuid4

        result = await delete_division(db, uuid4())

        assert result is False


class TestDivisionMembers:
    """Tests for division membership."""

    async def test_add_member_to_division(self, db: AsyncSession):
        """Test adding a member to a division."""
        division = await create_division(db, name="Test Division")
        person = await create_person(db, firstname="Member", lastname="Test")
        await db.flush()

        member = await add_division_member(
            db,
            division_id=division.id,
            person_id=person.id,
            role=DivisionRole.MEMBER,
        )
        await db.commit()

        assert member.id is not None
        assert member.division_id == division.id
        assert member.person_id == person.id
        assert member.role == DivisionRole.MEMBER

    async def test_add_admin_to_division(self, db: AsyncSession):
        """Test adding an admin to a division."""
        division = await create_division(db, name="Test Division")
        person = await create_person(db, firstname="Admin", lastname="Test")
        await db.flush()

        member = await add_division_member(
            db,
            division_id=division.id,
            person_id=person.id,
            role=DivisionRole.ADMIN,
        )
        await db.commit()

        assert member.role == DivisionRole.ADMIN

    async def test_get_division_membership(self, db: AsyncSession):
        """Test getting a specific membership."""
        division = await create_division(db, name="Test Division")
        person = await create_person(db, firstname="Member", lastname="Test")
        await db.flush()

        await add_division_member(db, division_id=division.id, person_id=person.id)
        await db.commit()

        membership = await get_division_membership(db, division.id, person.id)

        assert membership is not None
        assert membership.person_id == person.id

    async def test_update_division_member_role(self, db: AsyncSession):
        """Test updating a member's role."""
        division = await create_division(db, name="Test Division")
        person = await create_person(db, firstname="Member", lastname="Test")
        await db.flush()

        member = await add_division_member(
            db,
            division_id=division.id,
            person_id=person.id,
            role=DivisionRole.MEMBER,
        )
        await db.commit()

        updated = await update_division_member(db, member.id, role=DivisionRole.MANAGER)
        await db.commit()

        assert updated.role == DivisionRole.MANAGER

    async def test_list_division_members(self, db: AsyncSession):
        """Test listing all members of a division."""
        division = await create_division(db, name="Test Division")
        person1 = await create_person(db, firstname="Member1", lastname="Test")
        person2 = await create_person(db, firstname="Member2", lastname="Test")
        await db.flush()

        await add_division_member(db, division_id=division.id, person_id=person1.id)
        await add_division_member(db, division_id=division.id, person_id=person2.id)
        await db.commit()

        members = await list_division_members(db, division.id)

        assert len(members) == 2
        person_ids = [m.person_id for m in members]
        assert person1.id in person_ids
        assert person2.id in person_ids

    async def test_delete_division_member(self, db: AsyncSession):
        """Test removing a member from a division."""
        division = await create_division(db, name="Test Division")
        person = await create_person(db, firstname="Member", lastname="Test")
        await db.flush()

        member = await add_division_member(db, division_id=division.id, person_id=person.id)
        await db.commit()
        member_id = member.id

        result = await delete_division_member(db, member_id)
        await db.commit()

        assert result is True
        assert await get_division_member(db, member_id) is None
