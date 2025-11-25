from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedModifiedMixin, new_uuid

if TYPE_CHECKING:
    from app.models.person import Person
    from app.models.team import Team


class DivisionRole(str, Enum):
    """Roles a person can have within a division."""
    MEMBER = "member"
    MANAGER = "manager"
    ADMIN = "admin"


class Division(Base, CreatedModifiedMixin):
    """
    Division entity - hierarchical organizational unit.
    Can contain sub-divisions and teams.
    """

    __tablename__ = "divisions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Self-referential hierarchy
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("divisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    parent: Mapped[Optional["Division"]] = relationship(
        "Division",
        back_populates="sub_divisions",
        remote_side=[id],
        lazy="selectin",
    )

    sub_divisions: Mapped[list["Division"]] = relationship(
        "Division",
        back_populates="parent",
        lazy="selectin",
    )

    teams: Mapped[list["Team"]] = relationship(
        "Team",
        back_populates="division",
        lazy="selectin",
    )

    members: Mapped[list["DivisionMember"]] = relationship(
        "DivisionMember",
        back_populates="division",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Division {self.name} ({self.id})>"


class DivisionMember(Base, CreatedModifiedMixin):
    """
    Association between Person and Division with role.
    Defines what role a person has in a specific division.
    """

    __tablename__ = "division_members"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)

    division_id: Mapped[UUID] = mapped_column(
        ForeignKey("divisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[DivisionRole] = mapped_column(
        SQLEnum(DivisionRole, values_callable=lambda obj: [e.value for e in obj]),
        default=DivisionRole.MEMBER,
        nullable=False,
    )

    # Relationships
    division: Mapped["Division"] = relationship(
        "Division",
        back_populates="members",
        lazy="selectin",
    )

    person: Mapped["Person"] = relationship(
        "Person",
        back_populates="division_memberships",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<DivisionMember {self.person_id} in {self.division_id} as {self.role.value}>"
