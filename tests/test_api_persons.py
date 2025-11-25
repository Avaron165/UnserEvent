"""
API tests for persons endpoints.
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestListPersons:
    """Tests for list persons endpoint."""

    async def test_list_persons_requires_auth(self, client: AsyncClient):
        """Test listing persons requires authentication."""
        response = await client.get("/persons")
        assert response.status_code in (401, 403)

    async def test_list_persons_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing persons returns list (may contain test user's person)."""
        response = await client.get(
            "/persons",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_list_persons_with_data(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test listing persons returns created persons."""
        from tests.crud import create_person

        # Create some test persons
        person1 = await create_person(
            api_db,
            firstname="List",
            lastname="Test1",
            email=f"listtest1_{uuid4().hex[:8]}@example.com",
        )
        person2 = await create_person(
            api_db,
            firstname="List",
            lastname="Test2",
            email=f"listtest2_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.get(
            "/persons",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

        person_ids = [p["id"] for p in data]
        assert str(person1.id) in person_ids
        assert str(person2.id) in person_ids

    async def test_list_persons_pagination(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test listing persons with pagination."""
        from tests.crud import create_person

        # Create multiple persons
        for i in range(5):
            await create_person(
                api_db,
                firstname=f"Page{i}",
                lastname="Test",
                email=f"pagetest{i}_{uuid4().hex[:8]}@example.com",
            )
        await api_db.commit()

        # Test limit
        response = await client.get(
            "/persons?limit=2",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Test skip
        response = await client.get(
            "/persons?skip=1&limit=2",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_persons_search(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test listing persons with search filter."""
        from tests.crud import create_person

        unique_name = f"UniqueSearch{uuid4().hex[:6]}"
        person = await create_person(
            api_db,
            firstname=unique_name,
            lastname="Person",
            email=f"search_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.get(
            f"/persons?search={unique_name}",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(p["firstname"] == unique_name for p in data)


class TestCreatePerson:
    """Tests for create person endpoint."""

    async def test_create_person_requires_auth(self, client: AsyncClient):
        """Test creating person requires authentication."""
        response = await client.post(
            "/persons",
            json={
                "firstname": "Test",
                "lastname": "Person",
            },
        )
        assert response.status_code in (401, 403)

    async def test_create_person_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful person creation."""
        unique_email = f"create_{uuid4().hex[:8]}@example.com"
        response = await client.post(
            "/persons",
            headers={"Authorization": auth_headers["Authorization"]},
            json={
                "firstname": "Created",
                "lastname": "Person",
                "email": unique_email,
                "mobile": "+49123456789",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["firstname"] == "Created"
        assert data["lastname"] == "Person"
        assert data["email"] == unique_email
        assert data["mobile"] == "+49123456789"
        assert data["is_user"] is False
        assert "id" in data
        assert "created_at" in data

    async def test_create_person_minimal(self, client: AsyncClient, auth_headers: dict):
        """Test creating person with minimal fields."""
        response = await client.post(
            "/persons",
            headers={"Authorization": auth_headers["Authorization"]},
            json={
                "firstname": "Minimal",
                "lastname": "Person",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["firstname"] == "Minimal"
        assert data["lastname"] == "Person"
        assert data["email"] is None
        assert data["mobile"] is None

    async def test_create_person_missing_required(self, client: AsyncClient, auth_headers: dict):
        """Test creating person with missing required fields fails."""
        response = await client.post(
            "/persons",
            headers={"Authorization": auth_headers["Authorization"]},
            json={
                "firstname": "OnlyFirst",
            },
        )
        assert response.status_code == 422


class TestGetPerson:
    """Tests for get person endpoint."""

    async def test_get_person_requires_auth(self, client: AsyncClient):
        """Test getting person requires authentication."""
        response = await client.get(f"/persons/{uuid4()}")
        assert response.status_code in (401, 403)

    async def test_get_person_success(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test getting a person by ID."""
        from tests.crud import create_person

        person = await create_person(
            api_db,
            firstname="Get",
            lastname="Test",
            email=f"gettest_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.get(
            f"/persons/{person.id}",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(person.id)
        assert data["firstname"] == "Get"
        assert data["lastname"] == "Test"

    async def test_get_person_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting non-existent person returns 404."""
        response = await client.get(
            f"/persons/{uuid4()}",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 404
        assert "Person not found" in response.json()["detail"]

    async def test_get_person_invalid_uuid(self, client: AsyncClient, auth_headers: dict):
        """Test getting person with invalid UUID fails."""
        response = await client.get(
            "/persons/invalid-uuid",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 422


class TestUpdatePerson:
    """Tests for update person endpoint."""

    async def test_update_person_requires_auth(self, client: AsyncClient):
        """Test updating person requires authentication."""
        response = await client.patch(
            f"/persons/{uuid4()}",
            json={"firstname": "Updated"},
        )
        assert response.status_code in (401, 403)

    async def test_update_person_success_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test updating person as admin succeeds."""
        from tests.crud import create_person

        person = await create_person(
            api_db,
            firstname="Update",
            lastname="Test",
            email=f"update_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.patch(
            f"/persons/{person.id}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"firstname": "Updated"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["firstname"] == "Updated"
        assert data["lastname"] == "Test"

    async def test_update_person_partial(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test partial update only changes specified fields."""
        from tests.crud import create_person

        person = await create_person(
            api_db,
            firstname="Partial",
            lastname="Update",
            email=f"partial_{uuid4().hex[:8]}@example.com",
            mobile="+49111111111",
        )
        await api_db.commit()

        response = await client.patch(
            f"/persons/{person.id}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"mobile": "+49222222222"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["firstname"] == "Partial"  # Unchanged
        assert data["lastname"] == "Update"  # Unchanged
        assert data["mobile"] == "+49222222222"  # Changed

    async def test_update_person_not_found(self, client: AsyncClient, admin_headers: dict):
        """Test updating non-existent person returns 404."""
        response = await client.patch(
            f"/persons/{uuid4()}",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"firstname": "Updated"},
        )
        assert response.status_code == 404


class TestDeletePerson:
    """Tests for delete person endpoint."""

    async def test_delete_person_requires_auth(self, client: AsyncClient):
        """Test deleting person requires authentication."""
        response = await client.delete(f"/persons/{uuid4()}")
        assert response.status_code in (401, 403)

    async def test_delete_person_requires_admin(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test deleting person requires admin permission."""
        from tests.crud import create_person

        person = await create_person(
            api_db,
            firstname="Delete",
            lastname="Test",
            email=f"delete_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        # Regular user should not be able to delete
        response = await client.delete(
            f"/persons/{person.id}",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 403

    async def test_delete_person_as_admin(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test deleting person as admin succeeds."""
        from tests.crud import create_person

        person = await create_person(
            api_db,
            firstname="AdminDelete",
            lastname="Test",
            email=f"admindel_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.delete(
            f"/persons/{person.id}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 204

        # Verify person is deleted
        get_response = await client.get(
            f"/persons/{person.id}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert get_response.status_code == 404

    async def test_delete_person_not_found(self, client: AsyncClient, admin_headers: dict):
        """Test deleting non-existent person returns 404."""
        response = await client.delete(
            f"/persons/{uuid4()}",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 404


class TestPromotePersonToUser:
    """Tests for promoting person to user endpoint."""

    async def test_promote_requires_auth(self, client: AsyncClient):
        """Test promoting person requires authentication."""
        response = await client.post(
            f"/persons/{uuid4()}/promote",
            json={"username": "newuser", "password": "password"},
        )
        assert response.status_code in (401, 403)

    async def test_promote_requires_admin(
        self, client: AsyncClient, auth_headers: dict, api_db: AsyncSession
    ):
        """Test promoting person requires admin permission."""
        from tests.crud import create_person

        person = await create_person(
            api_db,
            firstname="Promote",
            lastname="Test",
            email=f"promote_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.post(
            f"/persons/{person.id}/promote",
            headers={"Authorization": auth_headers["Authorization"]},
            json={"username": "promoteduser", "password": "password123"},
        )
        assert response.status_code == 403

    async def test_promote_person_success(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession
    ):
        """Test promoting person to user succeeds."""
        from tests.crud import create_person

        unique_username = f"promoted_{uuid4().hex[:8]}"
        person = await create_person(
            api_db,
            firstname="ToPromote",
            lastname="Person",
            email=f"topromote_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.post(
            f"/persons/{person.id}/promote",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"username": unique_username, "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == unique_username
        assert data["is_active"] is True
        assert data["person"]["firstname"] == "ToPromote"

        # Verify the promoted user can login
        login_response = await client.post(
            "/auth/login",
            json={"username": unique_username, "password": "password123"},
        )
        assert login_response.status_code == 200

    async def test_promote_person_duplicate_username(
        self, client: AsyncClient, admin_headers: dict, api_db: AsyncSession, auth_user: dict
    ):
        """Test promoting with existing username fails."""
        from tests.crud import create_person

        person = await create_person(
            api_db,
            firstname="DupPromote",
            lastname="Test",
            email=f"duppromote_{uuid4().hex[:8]}@example.com",
        )
        await api_db.commit()

        response = await client.post(
            f"/persons/{person.id}/promote",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"username": auth_user["username"], "password": "password123"},
        )
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    async def test_promote_nonexistent_person(self, client: AsyncClient, admin_headers: dict):
        """Test promoting non-existent person fails."""
        response = await client.post(
            f"/persons/{uuid4()}/promote",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"username": "someuser", "password": "password123"},
        )
        assert response.status_code == 400

    async def test_promote_already_user(
        self, client: AsyncClient, admin_headers: dict, auth_user: dict
    ):
        """Test promoting person who is already a user fails."""
        response = await client.post(
            f"/persons/{auth_user['user'].id}/promote",
            headers={"Authorization": admin_headers["Authorization"]},
            json={"username": f"another_{uuid4().hex[:8]}", "password": "password123"},
        )
        assert response.status_code == 400
