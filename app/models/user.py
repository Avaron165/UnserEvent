from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.person import Person
    from app.models.auth import UserRole


class User(Base):
    """
    User entity - extends Person with login capability.
    Uses same ID as Person (1:1 relationship via shared primary key).
    """

    __tablename__ = "users"

    # Shared primary key with Person (1:1 relationship)
    id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        primary_key=True,
    )

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship back to Person
    person: Mapped["Person"] = relationship(
        "Person",
        back_populates="user",
        lazy="selectin",
    )

    # Relationship to roles
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        lazy="selectin",
    )

    @property
    def email(self) -> Optional[str]:
        """Get email from associated Person."""
        return self.person.email if self.person else None

    @property
    def full_name(self) -> str:
        """Get full name from associated Person."""
        return self.person.full_name if self.person else self.username

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.id})>"
