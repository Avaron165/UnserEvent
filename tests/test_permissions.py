"""
Tests for the permissions service, including superuser functionality.
"""
import pytest
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

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
from tests.crud import (
    create_user,
    create_division,
    create_team,
    create_person,
    add_division_member,
    add_team_member,
    assign_role_to_user,
    list_user_roles,
)
from app.models.division import DivisionRole
from app.models.team import TeamRole


class TestGlobalRoles:
    """Tests for global role checking functions."""

    @pytest.mark.asyncio
    async def test_is_superuser_returns_true_for_superuser(self, db: AsyncSession):
        """Test that is_superuser returns True for users with superuser role."""
        user = await create_user(
            db,
            firstname="Super",
            lastname="User",
            username=f"superuser_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "superuser")
        await db.commit()

        result = await is_superuser(db, user.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_superuser_returns_false_for_admin(self, db: AsyncSession):
        """Test that is_superuser returns False for users with only admin role."""
        user = await create_user(
            db,
            firstname="Admin",
            lastname="User",
            username=f"admin_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "admin")
        await db.commit()

        result = await is_superuser(db, user.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_superuser_returns_false_for_regular_user(self, db: AsyncSession):
        """Test that is_superuser returns False for regular users."""
        user = await create_user(
            db,
            firstname="Regular",
            lastname="User",
            username=f"regular_{uuid4().hex[:8]}",
            password="password123",
        )
        await db.commit()

        result = await is_superuser(db, user.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_admin_returns_true_for_admin(self, db: AsyncSession):
        """Test that is_admin returns True for users with admin role."""
        user = await create_user(
            db,
            firstname="Admin",
            lastname="User",
            username=f"admin_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "admin")
        await db.commit()

        result = await is_admin(db, user.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_admin_returns_false_for_superuser_only(self, db: AsyncSession):
        """Test that is_admin returns False for users with only superuser role."""
        user = await create_user(
            db,
            firstname="Super",
            lastname="User",
            username=f"superuser_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "superuser")
        await db.commit()

        result = await is_admin(db, user.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_has_elevated_privileges_for_superuser(self, db: AsyncSession):
        """Test that has_elevated_privileges returns True for superusers."""
        user = await create_user(
            db,
            firstname="Super",
            lastname="User",
            username=f"superuser_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "superuser")
        await db.commit()

        result = await has_elevated_privileges(db, user.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_elevated_privileges_for_admin(self, db: AsyncSession):
        """Test that has_elevated_privileges returns True for admins."""
        user = await create_user(
            db,
            firstname="Admin",
            lastname="User",
            username=f"admin_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "admin")
        await db.commit()

        result = await has_elevated_privileges(db, user.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_elevated_privileges_false_for_regular_user(self, db: AsyncSession):
        """Test that has_elevated_privileges returns False for regular users."""
        user = await create_user(
            db,
            firstname="Regular",
            lastname="User",
            username=f"regular_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "user")
        await db.commit()

        result = await has_elevated_privileges(db, user.id)
        assert result is False


class TestSuperuserDivisionPermissions:
    """Tests for superuser permissions on divisions."""

    @pytest.mark.asyncio
    async def test_superuser_can_manage_any_division(self, db: AsyncSession):
        """Test that a superuser can manage any division without membership."""
        superuser = await create_user(
            db,
            firstname="Super",
            lastname="User",
            username=f"superuser_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, superuser.id, "superuser")

        division = await create_division(db, name="Test Division")
        await db.commit()

        result = await can_manage_division(db, superuser.id, division.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_superuser_can_view_any_division(self, db: AsyncSession):
        """Test that a superuser can view any division without membership."""
        superuser = await create_user(
            db,
            firstname="Super",
            lastname="User",
            username=f"superuser_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, superuser.id, "superuser")

        division = await create_division(db, name="Test Division")
        await db.commit()

        result = await can_view_division(db, superuser.id, division.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_regular_user_cannot_manage_division_without_membership(self, db: AsyncSession):
        """Test that a regular user cannot manage a division without membership."""
        user = await create_user(
            db,
            firstname="Regular",
            lastname="User",
            username=f"regular_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "user")

        division = await create_division(db, name="Test Division")
        await db.commit()

        result = await can_manage_division(db, user.id, division.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_regular_user_cannot_view_division_without_membership(self, db: AsyncSession):
        """Test that a regular user cannot view a division without membership."""
        user = await create_user(
            db,
            firstname="Regular",
            lastname="User",
            username=f"regular_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "user")

        division = await create_division(db, name="Test Division")
        await db.commit()

        result = await can_view_division(db, user.id, division.id)
        assert result is False


class TestSuperuserTeamPermissions:
    """Tests for superuser permissions on teams."""

    @pytest.mark.asyncio
    async def test_superuser_can_manage_any_team(self, db: AsyncSession):
        """Test that a superuser can manage any team without membership."""
        superuser = await create_user(
            db,
            firstname="Super",
            lastname="User",
            username=f"superuser_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, superuser.id, "superuser")

        division = await create_division(db, name="Test Division")
        team = await create_team(db, name="Test Team", division_id=division.id)
        await db.commit()

        result = await can_manage_team(db, superuser.id, team.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_superuser_can_view_any_team(self, db: AsyncSession):
        """Test that a superuser can view any team without membership."""
        superuser = await create_user(
            db,
            firstname="Super",
            lastname="User",
            username=f"superuser_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, superuser.id, "superuser")

        division = await create_division(db, name="Test Division")
        team = await create_team(db, name="Test Team", division_id=division.id)
        await db.commit()

        result = await can_view_team(db, superuser.id, team.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_regular_user_cannot_manage_team_without_role(self, db: AsyncSession):
        """Test that a regular user cannot manage a team without appropriate role."""
        user = await create_user(
            db,
            firstname="Regular",
            lastname="User",
            username=f"regular_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "user")

        division = await create_division(db, name="Test Division")
        team = await create_team(db, name="Test Team", division_id=division.id)
        await db.commit()

        result = await can_manage_team(db, user.id, team.id)
        assert result is False


class TestSuperuserPersonPermissions:
    """Tests for superuser permissions on persons."""

    @pytest.mark.asyncio
    async def test_superuser_can_manage_any_person(self, db: AsyncSession):
        """Test that a superuser can manage any person."""
        superuser = await create_user(
            db,
            firstname="Super",
            lastname="User",
            username=f"superuser_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, superuser.id, "superuser")

        person = await create_person(
            db,
            firstname="Other",
            lastname="Person",
        )
        await db.commit()

        result = await can_manage_person(db, superuser.id, person.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_regular_user_cannot_manage_other_person(self, db: AsyncSession):
        """Test that a regular user cannot manage another person without relationship."""
        user = await create_user(
            db,
            firstname="Regular",
            lastname="User",
            username=f"regular_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "user")

        person = await create_person(
            db,
            firstname="Other",
            lastname="Person",
        )
        await db.commit()

        result = await can_manage_person(db, user.id, person.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_user_can_manage_self(self, db: AsyncSession):
        """Test that any user can manage themselves."""
        user = await create_user(
            db,
            firstname="Self",
            lastname="User",
            username=f"self_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "user")
        await db.commit()

        result = await can_manage_person(db, user.id, user.id)
        assert result is True


class TestAdminVsSuperuser:
    """Tests comparing admin and superuser permissions."""

    @pytest.mark.asyncio
    async def test_admin_can_manage_division(self, db: AsyncSession):
        """Test that admin can also manage any division."""
        admin = await create_user(
            db,
            firstname="Admin",
            lastname="User",
            username=f"admin_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, admin.id, "admin")

        division = await create_division(db, name="Test Division")
        await db.commit()

        result = await can_manage_division(db, admin.id, division.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_both_superuser_and_admin_roles(self, db: AsyncSession):
        """Test user with both superuser and admin roles."""
        user = await create_user(
            db,
            firstname="Both",
            lastname="Roles",
            username=f"both_{uuid4().hex[:8]}",
            password="password123",
        )
        await assign_role_to_user(db, user.id, "superuser")
        await assign_role_to_user(db, user.id, "admin")
        await db.commit()

        roles = await list_user_roles(db, user.id)
        assert "superuser" in roles
        assert "admin" in roles

        assert await is_superuser(db, user.id) is True
        assert await is_admin(db, user.id) is True
        assert await has_elevated_privileges(db, user.id) is True
