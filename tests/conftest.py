"""
Pytest configuration and fixtures for testing.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models import (
    Person, User, Division, DivisionMember,
    Team, TeamMember, Role, UserRole, RefreshToken
)


# ============================================================================
# MOCK REDIS FOR TESTING
# ============================================================================

class MockRedis:
    """In-memory mock Redis for testing."""

    def __init__(self):
        self._data = {}
        self._expiry = {}

    async def setex(self, key: str, seconds: int, value: str):
        """Set key with expiry."""
        self._data[key] = value
        self._expiry[key] = seconds

    async def get(self, key: str):
        """Get value by key."""
        return self._data.get(key)

    async def delete(self, *keys):
        """Delete keys."""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                self._expiry.pop(key, None)
                count += 1
        return count

    async def keys(self, pattern: str):
        """Get keys matching pattern."""
        import fnmatch
        return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]

    async def close(self):
        """Mock close."""
        pass


# Global mock redis instance for tests
_mock_redis = None


def get_mock_redis():
    """Get or create mock Redis instance."""
    global _mock_redis
    if _mock_redis is None:
        _mock_redis = MockRedis()
    return _mock_redis


def reset_mock_redis():
    """Reset mock Redis for test isolation."""
    global _mock_redis
    _mock_redis = MockRedis()


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture that provides a database session for each test.
    Creates a new engine per test to avoid event loop issues on Windows.
    """
    # Create engine per test to avoid event loop issues
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,  # Don't pool connections
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # Dispose engine after test
    await engine.dispose()


@pytest.fixture
async def db_with_rollback() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture that provides a database session with automatic rollback.
    Use this when you want to ensure test isolation without persistent changes.
    """
    # Create engine per test to avoid event loop issues
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.connect() as conn:
        await conn.begin()
        async with AsyncSession(bind=conn) as session:
            try:
                yield session
            finally:
                await conn.rollback()

    await engine.dispose()


@pytest.fixture
async def clean_db(db: AsyncSession) -> AsyncSession:
    """
    Fixture that cleans up the database before and after the test.
    Use with caution - this will delete all data!
    """
    from tests.crud import cleanup_all

    # Clean before test
    await cleanup_all(db)
    await db.commit()

    yield db

    # Clean after test
    await cleanup_all(db)
    await db.commit()


@pytest.fixture
async def sample_person(db: AsyncSession) -> Person:
    """Create a sample person for testing."""
    from tests.crud import create_person

    person = await create_person(
        db,
        firstname="Max",
        lastname="Mustermann",
        email="max@example.com",
        mobile="+49123456789",
    )
    await db.commit()
    return person


@pytest.fixture
async def sample_user(db: AsyncSession) -> User:
    """Create a sample user for testing."""
    from tests.crud import create_user

    user = await create_user(
        db,
        firstname="Admin",
        lastname="User",
        username="admin",
        password="password123",
        email="admin@example.com",
    )
    await db.commit()
    return user


@pytest.fixture
async def sample_division(db: AsyncSession) -> Division:
    """Create a sample division for testing."""
    from tests.crud import create_division

    division = await create_division(
        db,
        name="FC Hersbruck",
        description="Main club division",
    )
    await db.commit()
    return division


@pytest.fixture
async def sample_team(db: AsyncSession, sample_division: Division, sample_person: Person) -> Team:
    """Create a sample team for testing."""
    from tests.crud import create_team

    team = await create_team(
        db,
        name="U11",
        description="Under 11 team",
        division_id=sample_division.id,
        responsible_id=sample_person.id,
    )
    await db.commit()
    return team


@pytest.fixture
async def sample_proxy_team(db: AsyncSession) -> Team:
    """Create a sample proxy team for testing."""
    from tests.crud import create_proxy_team

    team = await create_proxy_team(
        db,
        name="FC Bayern U11",
        external_org="FC Bayern München",
        description="External team placeholder",
    )
    await db.commit()
    return team


# ============================================================================
# API TEST FIXTURES
# ============================================================================

@pytest.fixture
async def api_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session fixture for API tests.
    Creates a new engine per test to avoid event loop issues.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    await engine.dispose()


@pytest.fixture
async def client(api_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client for API testing.
    Overrides the database and Redis dependencies to use test instances.
    """
    import app.redis as redis_module

    async def override_get_db():
        yield api_db

    # Reset and patch mock Redis
    reset_mock_redis()
    original_get_redis = redis_module.get_redis

    async def mock_get_redis():
        return get_mock_redis()

    redis_module.get_redis = mock_get_redis

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    redis_module.get_redis = original_get_redis


@pytest.fixture
async def auth_user(api_db: AsyncSession) -> dict:
    """
    Create a test user and return user info with password.
    """
    from uuid import uuid4
    from tests.crud import create_user

    username = f"testuser_{uuid4().hex[:8]}"
    password = "testpassword123"

    user = await create_user(
        api_db,
        firstname="Test",
        lastname="User",
        username=username,
        password=password,
        email=f"{username}@example.com",
    )
    await api_db.commit()

    return {
        "user": user,
        "username": username,
        "password": password,
        "email": f"{username}@example.com",
    }


@pytest.fixture
async def auth_headers(client: AsyncClient, auth_user: dict) -> dict:
    """
    Get authentication headers for API requests.
    Logs in the test user and returns the Authorization header.
    """
    response = await client.post(
        "/auth/login",
        json={
            "username": auth_user["username"],
            "password": auth_user["password"],
        },
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    tokens = response.json()

    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "refresh_token": tokens["refresh_token"],
    }


@pytest.fixture
async def admin_user(api_db: AsyncSession) -> dict:
    """
    Create an admin user and return user info with password.
    """
    from uuid import uuid4
    from tests.crud import create_user, assign_role_to_user

    username = f"admin_{uuid4().hex[:8]}"
    password = "adminpassword123"

    user = await create_user(
        api_db,
        firstname="Admin",
        lastname="User",
        username=username,
        password=password,
        email=f"{username}@example.com",
    )
    await api_db.commit()

    # Assign admin role
    await assign_role_to_user(api_db, user.id, "admin")
    await api_db.commit()

    return {
        "user": user,
        "username": username,
        "password": password,
        "email": f"{username}@example.com",
    }


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: dict) -> dict:
    """
    Get admin authentication headers for API requests.
    """
    response = await client.post(
        "/auth/login",
        json={
            "username": admin_user["username"],
            "password": admin_user["password"],
        },
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    tokens = response.json()

    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "refresh_token": tokens["refresh_token"],
    }


@pytest.fixture
async def superuser(api_db: AsyncSession) -> dict:
    """
    Create a superuser and return user info with password.
    """
    from uuid import uuid4
    from tests.crud import create_user, assign_role_to_user

    username = f"superuser_{uuid4().hex[:8]}"
    password = "superpassword123"

    user = await create_user(
        api_db,
        firstname="Super",
        lastname="User",
        username=username,
        password=password,
        email=f"{username}@example.com",
    )
    await api_db.commit()

    # Assign superuser role
    await assign_role_to_user(api_db, user.id, "superuser")
    await api_db.commit()

    return {
        "user": user,
        "username": username,
        "password": password,
        "email": f"{username}@example.com",
    }


@pytest.fixture
async def superuser_headers(client: AsyncClient, superuser: dict) -> dict:
    """
    Get superuser authentication headers for API requests.
    """
    response = await client.post(
        "/auth/login",
        json={
            "username": superuser["username"],
            "password": superuser["password"],
        },
    )
    assert response.status_code == 200, f"Superuser login failed: {response.text}"
    tokens = response.json()

    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "refresh_token": tokens["refresh_token"],
    }
