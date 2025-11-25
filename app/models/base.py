from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr, relationship


def utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def new_uuid() -> UUID:
    """Generate a new UUID4."""
    return uuid4()


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class CreatedModifiedMixin:
    """Mixin for created_at/modified_at audit fields."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        server_default=func.now(),
    )

    modified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=utcnow,
        nullable=True,
    )

    @declared_attr
    def created_by_id(cls) -> Mapped[Optional[UUID]]:
        return mapped_column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )

    @declared_attr
    def modified_by_id(cls) -> Mapped[Optional[UUID]]:
        return mapped_column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )
