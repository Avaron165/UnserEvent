"""
API tests for authentication endpoints.
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns status ok."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data

    async def test_health_endpoint(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestLogin:
    """Tests for login endpoint."""

    async def test_login_success(self, client: AsyncClient, auth_user: dict):
        """Test successful login returns tokens."""
        response = await client.post(
            "/auth/login",
            json={
                "username": auth_user["username"],
                "password": auth_user["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_username(self, client: AsyncClient):
        """Test login with invalid username fails."""
        response = await client.post(
            "/auth/login",
            json={
                "username": "nonexistent_user",
                "password": "somepassword",
            },
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    async def test_login_invalid_password(self, client: AsyncClient, auth_user: dict):
        """Test login with invalid password fails."""
        response = await client.post(
            "/auth/login",
            json={
                "username": auth_user["username"],
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    async def test_login_missing_fields(self, client: AsyncClient):
        """Test login with missing fields fails."""
        response = await client.post(
            "/auth/login",
            json={"username": "test"},
        )
        assert response.status_code == 422  # Validation error

    async def test_login_with_device_info(self, client: AsyncClient, auth_user: dict):
        """Test login with device info stores it."""
        response = await client.post(
            "/auth/login",
            json={
                "username": auth_user["username"],
                "password": auth_user["password"],
                "device_info": "Test Device",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestRegister:
    """Tests for user registration endpoint."""

    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        username = f"newuser_{uuid4().hex[:8]}"
        response = await client.post(
            "/auth/register",
            json={
                "username": username,
                "password": "newpassword123",
                "firstname": "New",
                "lastname": "User",
                "email": f"{username}@example.com",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == username
        assert data["is_active"] is True
        assert "person" in data
        assert data["person"]["firstname"] == "New"
        assert data["person"]["lastname"] == "User"

    async def test_register_duplicate_username(self, client: AsyncClient, auth_user: dict):
        """Test registration with existing username fails."""
        response = await client.post(
            "/auth/register",
            json={
                "username": auth_user["username"],
                "password": "anotherpassword",
                "firstname": "Another",
                "lastname": "User",
            },
        )
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    async def test_register_minimal_fields(self, client: AsyncClient):
        """Test registration with minimal required fields."""
        username = f"minimal_{uuid4().hex[:8]}"
        response = await client.post(
            "/auth/register",
            json={
                "username": username,
                "password": "password123",
                "firstname": "Min",
                "lastname": "User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == username

    async def test_register_missing_required_fields(self, client: AsyncClient):
        """Test registration with missing required fields fails."""
        response = await client.post(
            "/auth/register",
            json={
                "username": "someuser",
                "password": "password123",
            },
        )
        assert response.status_code == 422


class TestRefreshToken:
    """Tests for token refresh endpoint."""

    async def test_refresh_token_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful token refresh."""
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": auth_headers["refresh_token"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should be different (rotation)
        assert data["refresh_token"] != auth_headers["refresh_token"]

    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refresh with invalid token fails."""
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )
        assert response.status_code == 401
        assert "Invalid or expired refresh token" in response.json()["detail"]

    async def test_refresh_token_reuse_after_rotation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that old refresh token is invalid after rotation."""
        old_refresh_token = auth_headers["refresh_token"]

        # First refresh - should succeed
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        assert response.status_code == 200

        # Second refresh with old token - should fail (token rotated)
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        assert response.status_code == 401


class TestLogout:
    """Tests for logout endpoints."""

    async def test_logout_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful logout revokes refresh token."""
        response = await client.post(
            "/auth/logout",
            headers={"Authorization": auth_headers["Authorization"]},
            json={"refresh_token": auth_headers["refresh_token"]},
        )
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]

        # Try to use the refresh token - should fail
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": auth_headers["refresh_token"]},
        )
        assert response.status_code == 401

    async def test_logout_without_auth(self, client: AsyncClient):
        """Test logout without authentication fails."""
        response = await client.post(
            "/auth/logout",
            json={"refresh_token": "some_token"},
        )
        assert response.status_code in (401, 403)

    async def test_logout_invalid_refresh_token(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test logout with invalid refresh token fails."""
        response = await client.post(
            "/auth/logout",
            headers={"Authorization": auth_headers["Authorization"]},
            json={"refresh_token": "invalid_token"},
        )
        assert response.status_code == 400
        assert "Invalid refresh token" in response.json()["detail"]

    async def test_logout_all_success(self, client: AsyncClient, auth_user: dict):
        """Test logout from all devices."""
        # Login multiple times to create multiple sessions
        tokens1 = (
            await client.post(
                "/auth/login",
                json={
                    "username": auth_user["username"],
                    "password": auth_user["password"],
                    "device_info": "Device 1",
                },
            )
        ).json()

        tokens2 = (
            await client.post(
                "/auth/login",
                json={
                    "username": auth_user["username"],
                    "password": auth_user["password"],
                    "device_info": "Device 2",
                },
            )
        ).json()

        # Logout from all devices
        response = await client.post(
            "/auth/logout-all",
            headers={"Authorization": f"Bearer {tokens1['access_token']}"},
        )
        assert response.status_code == 200
        assert "Logged out from" in response.json()["message"]

        # Both refresh tokens should be invalid now
        response1 = await client.post(
            "/auth/refresh",
            json={"refresh_token": tokens1["refresh_token"]},
        )
        response2 = await client.post(
            "/auth/refresh",
            json={"refresh_token": tokens2["refresh_token"]},
        )
        assert response1.status_code == 401
        assert response2.status_code == 401


class TestGetMe:
    """Tests for get current user endpoint."""

    async def test_get_me_success(self, client: AsyncClient, auth_headers: dict, auth_user: dict):
        """Test getting current user info."""
        response = await client.get(
            "/auth/me",
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == auth_user["username"]
        assert data["is_active"] is True
        assert "person" in data
        assert data["person"]["firstname"] == "Test"
        assert data["person"]["lastname"] == "User"
        assert "roles" in data
        assert isinstance(data["roles"], list)

    async def test_get_me_without_auth(self, client: AsyncClient):
        """Test getting current user without authentication fails."""
        response = await client.get("/auth/me")
        assert response.status_code in (401, 403)

    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token fails."""
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code in (401, 403)

    async def test_get_me_with_roles(
        self, client: AsyncClient, admin_headers: dict, admin_user: dict
    ):
        """Test getting current user shows roles."""
        response = await client.get(
            "/auth/me",
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == admin_user["username"]
        assert "admin" in data["roles"]
