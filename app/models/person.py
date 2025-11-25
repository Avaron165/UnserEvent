from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedModifiedMixin, new_uuid

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.team import TeamMember
    from app.models.division import DivisionMember


class Person(Base, CreatedModifiedMixin):
    """
    Person entity - base for contact information.
    Can exist without a User (login capability).
    Can be promoted to User later.
    """

    __tablename__ = "persons"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    lastname: Mapped[str] = mapped_column(String(255), nullable=False)
    firstname: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="person",
        uselist=False,
        lazy="selectin",
    )

    team_memberships: Mapped[list["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="person",
        lazy="selectin",
    )

    division_memberships: Mapped[list["DivisionMember"]] = relationship(
        "DivisionMember",
        back_populates="person",
        lazy="selectin",
    )

    @property
    def is_user(self) -> bool:
        """Check if this person has login capability."""
        return self.user is not None

    @property
    def full_name(self) -> str:
        """Return full name."""
        return f"{self.firstname} {self.lastname}"

    def __repr__(self) -> str:
        return f"<Person {self.full_name} ({self.id})>"
