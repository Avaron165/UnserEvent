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
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.base import Base
from app.models import (
    Person, User, Division, DivisionMember,
    Team, TeamMember, Role, UserRole, RefreshToken
)


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture that provides a database session for each test with automatic rollback.

    All changes made during the test are automatically rolled back at the end,
    so test data is cleaned up while pre-existing data remains untouched.

    Tests can still call commit() - it creates a savepoint instead of actually
    committing, so the rollback at the end undoes all changes.
    """
    # Create engine per test to avoid event loop issues on Windows
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.connect() as conn:
        # Start a transaction that we'll roll back at the end
        await conn.begin()

        # Use begin_nested() to create savepoints when session.commit() is called
        await conn.begin_nested()

        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            # Override commit to use savepoints instead of real commits
            @session.sync_session.event.listens_for(session.sync_session, "after_transaction_end")
            def restart_savepoint(session_sync, transaction):
                if transaction.nested and not transaction._parent.nested:
                    # Restart the savepoint after each commit
                    session_sync.begin_nested()

            try:
                yield session
            finally:
                # Roll back everything - this undoes all test changes
                await conn.rollback()

    await engine.dispose()


@pytest.fixture
async def db_persistent() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture that provides a database session that actually commits changes.
    Use this only when you need changes to persist (e.g., for integration tests).
    """
    # Create engine per test to avoid event loop issues
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
