from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.schemas.user import UserCreate, UserResponse, CurrentUserResponse
from app.services.auth import (
    authenticate_user,
    create_tokens_for_user,
    refresh_access_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    create_user,
)
from app.services.permissions import has_global_role


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user and return access/refresh tokens.
    """
    user = await authenticate_user(db, data.username, data.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Get device info from request if not provided
    device_info = data.device_info
    if device_info is None:
        user_agent = request.headers.get("user-agent", "")
        device_info = user_agent[:500] if user_agent else None

    access_token, refresh_token = await create_tokens_for_user(
        db, user, device_info
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh an access token using a refresh token.
    The refresh token is rotated (old one invalidated, new one returned).
    """
    result = await refresh_access_token(db, data.refresh_token)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token, new_refresh_token = result

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout")
async def logout(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Logout by revoking the refresh token.
    Requires valid access token.
    """
    success = await revoke_refresh_token(db, data.refresh_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token",
        )

    return {"message": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Logout from all devices by revoking all refresh tokens.
    """
    count = await revoke_all_user_tokens(db, current_user.id)

    return {"message": f"Logged out from {count} sessions"}


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the current authenticated user's information.
    """
    # Get roles
    roles = []
    for user_role in current_user.user_roles:
        roles.append(user_role.role.name)

    return CurrentUserResponse(
        id=current_user.id,
        username=current_user.username,
        is_active=current_user.is_active,
        last_login=current_user.last_login,
        person=current_user.person,
        roles=roles,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    Note: In production, you might want to restrict this endpoint
    or require admin approval.
    """
    # Check if username already exists
    from sqlalchemy import select
    from app.models.user import User as UserModel

    stmt = select(UserModel).where(UserModel.username == data.username)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = await create_user(
        db,
        username=data.username,
        password=data.password,
        firstname=data.firstname,
        lastname=data.lastname,
        email=data.email,
        mobile=data.mobile,
    )

    return UserResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        last_login=user.last_login,
        person=user.person,
    )
