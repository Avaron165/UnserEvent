"""
Pytest configuration and fixtures for testing.
"""
import asyncio
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models.base import Base
from app.models import (
    Person, User, Division, DivisionMember,
    Team, TeamMember, Role, UserRole, RefreshToken
)


# Create test engine
test_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture that provides a database session for each test.
    Each test gets its own transaction that is rolled back after the test.
    """
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
async def db_with_rollback() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture that provides a database session with automatic rollback.
    Use this when you want to ensure test isolation without persistent changes.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        async with AsyncSession(bind=conn) as session:
            try:
                yield session
            finally:
                await conn.rollback()


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
