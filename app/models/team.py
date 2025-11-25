from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedModifiedMixin, new_uuid

if TYPE_CHECKING:
    from app.models.person import Person
    from app.models.division import Division


class TeamRole(str, Enum):
    """Roles a person can have within a team."""
    PLAYER = "player"
    COACH = "coach"
    MANAGER = "manager"
    MEDIC = "medic"
    STAFF = "staff"


class Team(Base, CreatedModifiedMixin):
    """
    Team entity.
    Can be a proxy team (external, without full details) or a full team.
    Proxy teams have no responsible person and can be promoted later.
    """

    __tablename__ = "teams"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Division relationship (NULL for external teams)
    division_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("divisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # External organization name (for proxy teams from other orgs)
    external_org: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Responsible person (NULL = proxy team)
    responsible_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
    )

    # When was this proxy promoted to a full team?
    promoted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    division: Mapped[Optional["Division"]] = relationship(
        "Division",
        back_populates="teams",
        lazy="selectin",
    )

    responsible: Mapped[Optional["Person"]] = relationship(
        "Person",
        foreign_keys=[responsible_id],
        lazy="selectin",
    )

    members: Mapped[list["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="team",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def is_proxy(self) -> bool:
        """Check if this is a proxy team (no responsible person)."""
        return self.responsible_id is None

    @property
    def is_external(self) -> bool:
        """Check if this is an external team (no division)."""
        return self.division_id is None

    def __repr__(self) -> str:
        proxy_str = " (proxy)" if self.is_proxy else ""
        return f"<Team {self.name}{proxy_str} ({self.id})>"


class TeamMember(Base, CreatedModifiedMixin):
    """
    Association between Person and Team with role.
    Defines what role a person has in a specific team.
    """

    __tablename__ = "team_members"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)

    team_id: Mapped[UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[TeamRole] = mapped_column(
        SQLEnum(TeamRole),
        default=TeamRole.PLAYER,
        nullable=False,
    )

    # Relationships
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="members",
        lazy="selectin",
    )

    person: Mapped["Person"] = relationship(
        "Person",
        back_populates="team_memberships",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<TeamMember {self.person_id} in {self.team_id} as {self.role.value}>"
