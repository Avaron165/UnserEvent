"""
API tests for divisions endpoints.
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestListDivisions:
    """Tests for list divisions endpoint."""

    async def test_list_divisions_requires_auth(self, client: AsyncClient):
        """Test listing divisions requires authentication."""
        response = await client.get("/divisions")
        assert response.status_code == 401

    async def test_list_divisions_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing divisions when empty returns empty list."""
        response = await client.get(
            "/divisions",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_divisions_with_data(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test listing divisions returns created divisions."""
        from tests.crud import create_division

        division1 = await create_division(api_db, name=f"Div1_{uuid4().hex[:6]}")
        division2 = await create_division(api_db, name=f"Div2_{uuid4().hex[:6]}")
        await api_db.commit()

        response = await client.get(
            "/divisions",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

        division_ids = [d["id"] for d in data]
        assert str(division1.id) in division_ids
        assert str(division2.id) in division_ids

    async def test_list_divisions_root_only(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test listing only root divisions."""
        from tests.crud import create_division

        root = await create_division(api_db, name=f"Root_{uuid4().hex[:6]}")
        await api_db.commit()
        child = await create_division(
            api_db, name=f"Child_{uuid4().hex[:6]}", parent_id=root.id
        )
        await api_db.commit()

        response = await client.get(
            "/divisions?root_only=true",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()

        division_ids = [d["id"] for d in data]
        assert str(root.id) in division_ids
        assert str(child.id) not in division_ids

    async def test_list_divisions_by_parent(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test listing divisions by parent_id."""
        from tests.crud import create_division

        parent = await create_division(api_db, name=f"Parent_{uuid4().hex[:6]}")
        await api_db.commit()
        child1 = await create_division(
            api_db, name=f"Child1_{uuid4().hex[:6]}", parent_id=parent.id
        )
        child2 = await create_division(
            api_db, name=f"Child2_{uuid4().hex[:6]}", parent_id=parent.id
        )
        await api_db.commit()

        response = await client.get(
            f"/divisions?parent_id={parent.id}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()

        division_ids = [d["id"] for d in data]
        assert str(child1.id) in division_ids
        assert str(child2.id) in division_ids
        assert str(parent.id) not in division_ids

    async def test_list_divisions_pagination(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test listing divisions with pagination."""
        from tests.crud import create_division

        for i in range(5):
            await create_division(api_db, name=f"PageDiv{i}_{uuid4().hex[:6]}")
        await api_db.commit()

        response = await client.get(
            "/divisions?limit=2",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestGetDivisionTree:
    """Tests for division tree endpoint."""

    async def test_get_tree_requires_auth(self, client: AsyncClient):
        """Test getting division tree requires authentication."""
        response = await client.get("/divisions/tree")
        assert response.status_code == 401

    async def test_get_tree_empty(self, client: AsyncClient, auth_headers: dict):
        """Test getting division tree when empty."""
        response = await client.get(
            "/divisions/tree",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_tree_with_hierarchy(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test getting division tree with nested structure."""
        from tests.crud import create_division

        root = await create_division(api_db, name=f"TreeRoot_{uuid4().hex[:6]}")
        await api_db.commit()
        child = await create_division(
            api_db, name=f"TreeChild_{uuid4().hex[:6]}", parent_id=root.id
        )
        await api_db.commit()
        grandchild = await create_division(
            api_db, name=f"TreeGrandchild_{uuid4().hex[:6]}", parent_id=child.id
        )
        await api_db.commit()

        response = await client.get(
            "/divisions/tree",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()

        # Find our root division
        root_div = next((d for d in data if d["id"] == str(root.id)), None)
        assert root_div is not None
        assert "sub_divisions" in root_div
        assert len(root_div["sub_divisions"]) >= 1

        child_div = next(
            (d for d in root_div["sub_divisions"] if d["id"] == str(child.id)), None
        )
        assert child_div is not None
        assert len(child_div["sub_divisions"]) >= 1


class TestCreateDivision:
    """Tests for create division endpoint."""

    async def test_create_division_requires_auth(self, client: AsyncClient):
        """Test creating division requires authentication."""
        response = await client.post(
            "/divisions",
            json={"name": "Test Division"},
        )
        assert response.status_code == 401

    async def test_create_root_division_requires_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating root division requires admin permission."""
        response = await client.post(
            "/divisions",
            headers={"Authorization": auth_headers["Authorization"]},
            json={"name": "Root Division"},
        )
        assert response.status_code == 403
        assert "Admin permission required" in response.json()["detail"]

    async def test_create_root_division_as_admin(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test creating root division as admin succeeds."""
        unique_name = f"AdminRoot_{uuid4().hex[:6]}"
        response = await client.post(
            "/divisions",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "name": unique_name,
                "description": "Created by admin",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == unique_name
        assert data["description"] == "Created by admin"
        assert data["parent_id"] is None
        assert "id" in data
        assert "created_at" in data

    async def test_create_sub_division_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test creating sub-division under existing division."""
        from tests.crud import create_division

        parent = await create_division(api_db, name=f"SubParent_{uuid4().hex[:6]}")
        await api_db.commit()

        unique_name = f"SubChild_{uuid4().hex[:6]}"
        response = await client.post(
            "/divisions",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "name": unique_name,
                "parent_id": str(parent.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == unique_name
        assert data["parent_id"] == str(parent.id)

    async def test_create_division_invalid_parent(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test creating division with non-existent parent fails."""
        response = await client.post(
            "/divisions",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "name": "Orphan Division",
                "parent_id": str(uuid4()),
            },
        )
        assert response.status_code == 400
        assert "Parent division not found" in response.json()["detail"]

    async def test_create_division_missing_name(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test creating division without name fails."""
        response = await client.post(
            "/divisions",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"description": "No name"},
        )
        assert response.status_code == 422


class TestGetDivision:
    """Tests for get division endpoint."""

    async def test_get_division_requires_auth(self, client: AsyncClient):
        """Test getting division requires authentication."""
        response = await client.get(f"/divisions/{uuid4()}")
        assert response.status_code == 401

    async def test_get_division_success(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test getting a division by ID."""
        from tests.crud import create_division

        division = await create_division(
            api_db,
            name=f"GetDiv_{uuid4().hex[:6]}",
            description="Test description",
        )
        await api_db.commit()

        response = await client.get(
            f"/divisions/{division.id}",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(division.id)
        assert data["name"] == division.name
        assert data["description"] == "Test description"

    async def test_get_division_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting non-existent division returns 404."""
        response = await client.get(
            f"/divisions/{uuid4()}",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 404
        assert "Division not found" in response.json()["detail"]


class TestUpdateDivision:
    """Tests for update division endpoint."""

    async def test_update_division_requires_auth(self, client: AsyncClient):
        """Test updating division requires authentication."""
        response = await client.patch(
            f"/divisions/{uuid4()}",
            json={"name": "Updated"},
        )
        assert response.status_code == 401

    async def test_update_division_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test updating division as admin."""
        from tests.crud import create_division

        division = await create_division(api_db, name=f"UpdateDiv_{uuid4().hex[:6]}")
        await api_db.commit()

        response = await client.patch(
            f"/divisions/{division.id}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "name": "Updated Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    async def test_update_division_partial(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test partial division update."""
        from tests.crud import create_division

        division = await create_division(
            api_db,
            name=f"PartialDiv_{uuid4().hex[:6]}",
            description="Original description",
        )
        await api_db.commit()

        response = await client.patch(
            f"/divisions/{division.id}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"description": "New description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == division.name  # Unchanged
        assert data["description"] == "New description"

    async def test_update_division_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test updating non-existent division returns 404."""
        response = await client.patch(
            f"/divisions/{uuid4()}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"name": "Updated"},
        )
        assert response.status_code == 404


class TestDeleteDivision:
    """Tests for delete division endpoint."""

    async def test_delete_division_requires_auth(self, client: AsyncClient):
        """Test deleting division requires authentication."""
        response = await client.delete(f"/divisions/{uuid4()}")
        assert response.status_code == 401

    async def test_delete_division_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test deleting division as admin."""
        from tests.crud import create_division

        division = await create_division(api_db, name=f"DeleteDiv_{uuid4().hex[:6]}")
        await api_db.commit()

        response = await client.delete(
            f"/divisions/{division.id}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 204

        # Verify deletion
        get_response = await client.get(
            f"/divisions/{division.id}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert get_response.status_code == 404

    async def test_delete_division_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test deleting non-existent division returns 404."""
        response = await client.delete(
            f"/divisions/{uuid4()}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 404


class TestDivisionMembers:
    """Tests for division member endpoints."""

    async def test_list_members_requires_auth(self, client: AsyncClient):
        """Test listing division members requires authentication."""
        response = await client.get(f"/divisions/{uuid4()}/members")
        assert response.status_code == 401

    async def test_list_members_empty(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test listing members of division with no members."""
        from tests.crud import create_division

        division = await create_division(api_db, name=f"EmptyDiv_{uuid4().hex[:6]}")
        await api_db.commit()

        response = await client.get(
            f"/divisions/{division.id}/members",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_members_with_data(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test listing division members."""
        from tests.crud import create_division, create_person, add_division_member

        division = await create_division(api_db, name=f"MemberDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="Member",
            lastname="Person",
            email=f"member_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        member = await add_division_member(
            api_db, division_id=division.id, person_id=person.id
        )
        await api_db.commit()

        response = await client.get(
            f"/divisions/{division.id}/members",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["person_id"] == str(person.id)

    async def test_add_member_requires_auth(self, client: AsyncClient):
        """Test adding division member requires authentication."""
        response = await client.post(
            f"/divisions/{uuid4()}/members",
            json={"person_id": str(uuid4()), "role": "MEMBER"},
        )
        assert response.status_code == 401

    async def test_add_member_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test adding member to division as admin."""
        from tests.crud import create_division, create_person

        division = await create_division(api_db, name=f"AddMemberDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="NewMember",
            lastname="Person",
            email=f"newmember_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.post(
            f"/divisions/{division.id}/members",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "person_id": str(person.id),
                "role": "MEMBER",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["person_id"] == str(person.id)
        assert data["division_id"] == str(division.id)
        assert data["role"] == "MEMBER"

    async def test_add_member_as_manager(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test adding member with MANAGER role."""
        from tests.crud import create_division, create_person

        division = await create_division(api_db, name=f"ManagerDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="Manager",
            lastname="Person",
            email=f"manager_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.post(
            f"/divisions/{division.id}/members",
            headers={"Authorization": admin_headers["Authorization"]},
            json={
                "person_id": str(person.id),
                "role": "MANAGER",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "MANAGER"

    async def test_remove_member_requires_auth(self, client: AsyncClient):
        """Test removing division member requires authentication."""
        response = await client.delete(
            f"/divisions/{uuid4()}/members/{uuid4()}"
        )
        assert response.status_code == 401

    async def test_remove_member_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test removing member from division as admin."""
        from tests.crud import create_division, create_person, add_division_member

        division = await create_division(api_db, name=f"RemMemberDiv_{uuid4().hex[:6]}")
        person = await create_person(
            api_db,
            firstname="RemoveMember",
            lastname="Person",
            email=f"remmember_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        member = await add_division_member(
            api_db, division_id=division.id, person_id=person.id
        )
        await api_db.commit()

        response = await client.delete(
            f"/divisions/{division.id}/members/{member.id}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 204

        # Verify removal
        list_response = await client.get(
            f"/divisions/{division.id}/members",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) == 0

    async def test_remove_member_not_found(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test removing non-existent member returns 404."""
        from tests.crud import create_division

        division = await create_division(api_db, name=f"NoMemberDiv_{uuid4().hex[:6]}")
        await api_db.commit()

        response = await client.delete(
            f"/divisions/{division.id}/members/{uuid4()}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 404
