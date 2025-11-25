from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedModifiedMixin, new_uuid

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base):
    """
    Global role for authorization.
    Examples: admin, user, readonly
    """

    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class UserRole(Base):
    """
    Association between User and Role.
    A user can have multiple global roles.
    """

    __tablename__ = "user_roles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_roles",
        lazy="selectin",
    )

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="user_roles",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    def __repr__(self) -> str:
        return f"<UserRole {self.user_id} has {self.role_id}>"


class RefreshToken(Base):
    """
    Refresh token stored in database for audit and revocation.
    Actual token validation happens in Redis for performance.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Hash of the token (never store plain tokens)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Device/client info for tracking sessions
    device_info: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Revocation timestamp (NULL = active)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")

    @property
    def is_revoked(self) -> bool:
        """Check if token has been revoked."""
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        from app.models.base import utcnow
        return self.expires_at < utcnow()

    @property
    def is_valid(self) -> bool:
        """Check if token is still valid (not revoked and not expired)."""
        return not self.is_revoked and not self.is_expired

    def __repr__(self) -> str:
        status = "revoked" if self.is_revoked else ("expired" if self.is_expired else "active")
        return f"<RefreshToken {self.id} ({status})>"
