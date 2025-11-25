"""
Tests for User CRUD and role operations.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth import verify_password
from tests.crud import (
    create_user,
    create_user_for_person,
    get_user,
    get_user_by_username,
    update_user,
    delete_user,
    list_users,
    create_person,
    assign_role_to_user,
    remove_role_from_user,
    list_user_roles,
)


class TestUserCreate:
    """Tests for creating users."""

    async def test_create_user(self, db: AsyncSession):
        """Test creating a user with all fields."""
        user = await create_user(
            db,
            firstname="Test",
            lastname="User",
            username="testuser",
            password="password123",
            email="test@example.com",
            mobile="+49123456789",
        )
        await db.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.person is not None
        assert user.person.firstname == "Test"
        assert user.person.lastname == "User"
        assert user.person.email == "test@example.com"

    async def test_user_password_hashed(self, db: AsyncSession):
        """Test that password is properly hashed."""
        user = await create_user(
            db,
            firstname="Test",
            lastname="User",
            username="hashtest",
            password="mypassword",
        )
        await db.commit()

        # Password should be hashed, not plain text
        assert user.password_hash != "mypassword"
        assert verify_password("mypassword", user.password_hash) is True
        assert verify_password("wrongpassword", user.password_hash) is False

    async def test_promote_person_to_user(self, db: AsyncSession):
        """Test promoting an existing person to a user."""
        # Create person first
        person = await create_person(
            db,
            firstname="Existing",
            lastname="Person",
            email="existing@example.com",
        )
        await db.commit()

        assert person.is_user is False

        # Promote to user
        user = await create_user_for_person(
            db,
            person.id,
            username="existinguser",
            password="password123",
        )
        await db.commit()

        assert user is not None
        assert user.id == person.id
        assert user.username == "existinguser"

        # Refresh person and check
        await db.refresh(person)
        assert person.is_user is True

    async def test_promote_already_user(self, db: AsyncSession):
        """Test that promoting an existing user fails."""
        user = await create_user(
            db,
            firstname="Already",
            lastname="User",
            username="alreadyuser",
            password="password123",
        )
        await db.commit()

        # Try to promote again
        result = await create_user_for_person(
            db,
            user.id,
            username="duplicate",
            password="password456",
        )

        assert result is None


class TestUserRead:
    """Tests for reading users."""

    async def test_get_user_by_id(self, db: AsyncSession):
        """Test getting a user by ID."""
        created = await create_user(
            db,
            firstname="Get",
            lastname="Test",
            username="gettest",
            password="password",
        )
        await db.commit()

        fetched = await get_user(db, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.person is not None

    async def test_get_user_not_found(self, db: AsyncSession):
        """Test getting a non-existent user."""
        from uuid import uuid4

        user = await get_user(db, uuid4())

        assert user is None

    async def test_get_user_by_username(self, db: AsyncSession):
        """Test getting a user by username."""
        await create_user(
            db,
            firstname="Username",
            lastname="Test",
            username="uniqueusername",
            password="password",
        )
        await db.commit()

        user = await get_user_by_username(db, "uniqueusername")

        assert user is not None
        assert user.username == "uniqueusername"

    async def test_list_users(self, db: AsyncSession):
        """Test listing users."""
        await create_user(db, firstname="List1", lastname="User", username="listuser1", password="pass")
        await create_user(db, firstname="List2", lastname="User", username="listuser2", password="pass")
        await db.commit()

        users = await list_users(db)

        usernames = [u.username for u in users]
        assert "listuser1" in usernames
        assert "listuser2" in usernames


class TestUserUpdate:
    """Tests for updating users."""

    async def test_update_username(self, db: AsyncSession):
        """Test updating a user's username."""
        user = await create_user(
            db,
            firstname="Update",
            lastname="Test",
            username="oldusername",
            password="password",
        )
        await db.commit()

        updated = await update_user(db, user.id, username="newusername")
        await db.commit()

        assert updated.username == "newusername"

    async def test_update_password(self, db: AsyncSession):
        """Test updating a user's password."""
        user = await create_user(
            db,
            firstname="Password",
            lastname="Test",
            username="passuser",
            password="oldpassword",
        )
        await db.commit()

        updated = await update_user(db, user.id, password="newpassword")
        await db.commit()

        assert verify_password("newpassword", updated.password_hash) is True
        assert verify_password("oldpassword", updated.password_hash) is False

    async def test_deactivate_user(self, db: AsyncSession):
        """Test deactivating a user."""
        user = await create_user(
            db,
            firstname="Active",
            lastname="User",
            username="activeuser",
            password="password",
        )
        await db.commit()

        assert user.is_active is True

        updated = await update_user(db, user.id, is_active=False)
        await db.commit()

        assert updated.is_active is False


class TestUserDelete:
    """Tests for deleting users."""

    async def test_delete_user_keeps_person(self, db: AsyncSession):
        """Test that deleting a user keeps the person."""
        user = await create_user(
            db,
            firstname="Delete",
            lastname="Test",
            username="deleteuser",
            password="password",
        )
        await db.commit()

        user_id = user.id
        person_id = user.person.id

        result = await delete_user(db, user_id)
        await db.commit()

        assert result is True

        # User should be gone
        assert await get_user(db, user_id) is None

        # Person should still exist
        from tests.crud import get_person

        person = await get_person(db, person_id)
        assert person is not None
        assert person.is_user is False


class TestUserRoles:
    """Tests for user role management."""

    async def test_assign_role_to_user(self, db: AsyncSession):
        """Test assigning a global role to a user."""
        user = await create_user(
            db,
            firstname="Role",
            lastname="Test",
            username="roleuser",
            password="password",
        )
        await db.commit()

        result = await assign_role_to_user(db, user.id, "admin")
        await db.commit()

        assert result is not None

        roles = await list_user_roles(db, user.id)
        assert "admin" in roles

    async def test_assign_multiple_roles(self, db: AsyncSession):
        """Test assigning multiple roles to a user."""
        user = await create_user(
            db,
            firstname="Multi",
            lastname="Role",
            username="multirole",
            password="password",
        )
        await db.commit()

        await assign_role_to_user(db, user.id, "admin")
        await assign_role_to_user(db, user.id, "user")
        await db.commit()

        roles = await list_user_roles(db, user.id)
        assert "admin" in roles
        assert "user" in roles

    async def test_remove_role_from_user(self, db: AsyncSession):
        """Test removing a role from a user."""
        user = await create_user(
            db,
            firstname="Remove",
            lastname="Role",
            username="removerole",
            password="password",
        )
        await db.commit()

        await assign_role_to_user(db, user.id, "admin")
        await db.commit()

        roles_before = await list_user_roles(db, user.id)
        assert "admin" in roles_before

        result = await remove_role_from_user(db, user.id, "admin")
        await db.commit()

        assert result is True

        roles_after = await list_user_roles(db, user.id)
        assert "admin" not in roles_after

    async def test_assign_nonexistent_role(self, db: AsyncSession):
        """Test assigning a non-existent role."""
        user = await create_user(
            db,
            firstname="Bad",
            lastname="Role",
            username="badrole",
            password="password",
        )
        await db.commit()

        result = await assign_role_to_user(db, user.id, "nonexistent")

        assert result is None

    async def test_assign_duplicate_role(self, db: AsyncSession):
        """Test assigning the same role twice."""
        user = await create_user(
            db,
            firstname="Dup",
            lastname="Role",
            username="duprole",
            password="password",
        )
        await db.commit()

        result1 = await assign_role_to_user(db, user.id, "admin")
        await db.commit()

        result2 = await assign_role_to_user(db, user.id, "admin")

        # Second call should return existing assignment
        assert result1 is not None
        assert result2 is not None
        assert result1.id == result2.id

        roles = await list_user_roles(db, user.id)
        assert roles.count("admin") == 1
