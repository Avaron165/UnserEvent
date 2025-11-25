from dataclasses import dataclass, field
from enum import Enum

from classes import CreatedModifiedMixin
from classes.person import Person

from uuid import UUID
from classes.uuid_utils import new_id
from classes.team import Team

class TeamRole(Enum):
    PLAYER = "player"
    COACH = "coach"
    MANAGER = "manager"
    MEDIC = "medic"
    STAFF = "staff"

@dataclass(kw_only=True)
class TeamMember(CreatedModifiedMixin):
    id: UUID = field(default_factory=new_id)
    person: Person
    role: TeamRole
    team: Team

    def __str__(self):
        return f"{self.person}, Role: {self.role.value}, Team: {self.team.name}"