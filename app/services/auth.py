import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.auth import RefreshToken
from app.models.user import User
from app.models.person import Person
from app.redis import get_redis


ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        ph.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def hash_token(token: str) -> str:
    """Hash a refresh token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: UUID, username: str) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token() -> tuple[str, datetime]:
    """Create a refresh token and its expiration datetime."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return token, expires_at


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> Optional[User]:
    """Authenticate a user by username and password."""
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    return user


async def create_tokens_for_user(
    db: AsyncSession,
    user: User,
    device_info: Optional[str] = None,
) -> tuple[str, str]:
    """Create access and refresh tokens for a user."""
    # Create access token (JWT)
    access_token = create_access_token(user.id, user.username)

    # Create refresh token
    refresh_token, expires_at = create_refresh_token()
    token_hash = hash_token(refresh_token)

    # Store in database
    db_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        device_info=device_info,
        created_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )
    db.add(db_token)
    await db.commit()

    # Store in Redis for fast lookup
    redis = await get_redis()
    ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    await redis.setex(
        f"refresh:{token_hash}",
        ttl_seconds,
        str(user.id),
    )

    # Track user sessions
    await redis.sadd(f"user_sessions:{user.id}", token_hash)

    return access_token, refresh_token


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
) -> Optional[tuple[str, str]]:
    """
    Refresh an access token using a refresh token.
    Returns new access token and optionally rotates refresh token.
    """
    token_hash = hash_token(refresh_token)

    # Check Redis first (fast path)
    redis = await get_redis()
    user_id_str = await redis.get(f"refresh:{token_hash}")

    if user_id_str is None:
        return None

    user_id = UUID(user_id_str)

    # Verify token in database (not revoked)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()

    if db_token is None or not db_token.is_valid:
        # Token was revoked or expired, clean up Redis
        await redis.delete(f"refresh:{token_hash}")
        await redis.srem(f"user_sessions:{user_id}", token_hash)
        return None

    # Get user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None

    # Create new access token
    access_token = create_access_token(user.id, user.username)

    # Token rotation: create new refresh token and revoke old one
    new_refresh_token, new_expires_at = create_refresh_token()
    new_token_hash = hash_token(new_refresh_token)

    # Revoke old token
    db_token.revoked_at = datetime.now(timezone.utc)

    # Create new token
    new_db_token = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        device_info=db_token.device_info,
        created_at=datetime.now(timezone.utc),
        expires_at=new_expires_at,
    )
    db.add(new_db_token)
    await db.commit()

    # Update Redis
    await redis.delete(f"refresh:{token_hash}")
    await redis.srem(f"user_sessions:{user_id}", token_hash)

    ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    await redis.setex(f"refresh:{new_token_hash}", ttl_seconds, str(user.id))
    await redis.sadd(f"user_sessions:{user_id}", new_token_hash)

    return access_token, new_refresh_token


async def revoke_refresh_token(
    db: AsyncSession,
    refresh_token: str,
) -> bool:
    """Revoke a specific refresh token (logout from one device)."""
    token_hash = hash_token(refresh_token)

    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()

    if db_token is None:
        return False

    db_token.revoked_at = datetime.now(timezone.utc)
    await db.commit()

    # Remove from Redis
    redis = await get_redis()
    await redis.delete(f"refresh:{token_hash}")
    await redis.srem(f"user_sessions:{db_token.user_id}", token_hash)

    return True


async def revoke_all_user_tokens(
    db: AsyncSession,
    user_id: UUID,
) -> int:
    """Revoke all refresh tokens for a user (logout from all devices)."""
    now = datetime.now(timezone.utc)

    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()

    count = 0
    redis = await get_redis()

    for token in tokens:
        token.revoked_at = now
        await redis.delete(f"refresh:{token.token_hash}")
        count += 1

    await db.commit()

    # Clear user sessions set
    await redis.delete(f"user_sessions:{user_id}")

    return count


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get a user by ID."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    firstname: str,
    lastname: str,
    email: Optional[str] = None,
    mobile: Optional[str] = None,
) -> User:
    """Create a new user with associated person."""
    # Create person first
    person = Person(
        firstname=firstname,
        lastname=lastname,
        email=email,
        mobile=mobile,
    )
    db.add(person)
    await db.flush()  # Get person.id

    # Create user with same ID
    user = User(
        id=person.id,
        username=username,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def promote_person_to_user(
    db: AsyncSession,
    person_id: UUID,
    username: str,
    password: str,
) -> Optional[User]:
    """Promote an existing person to a user (add login capability)."""
    # Check if person exists
    stmt = select(Person).where(Person.id == person_id)
    result = await db.execute(stmt)
    person = result.scalar_one_or_none()

    if person is None:
        return None

    # Check if already a user
    if person.is_user:
        return None

    # Create user
    user = User(
        id=person.id,
        username=username,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
