from dataclasses import dataclass, field

from classes import CreatedModifiedMixin
from classes.person import Person
from classes.participant import Participant
from typing import List, TYPE_CHECKING
from uuid import UUID
from classes.uuid_utils import new_id
from classes.division import Division
from textwrap import indent

if TYPE_CHECKING:
    from classes.team_member import TeamMember


@dataclass(kw_only=True)
class Team(Participant, Division, CreatedModifiedMixin):
    id: UUID = field(default_factory=new_id)
    responsible: Person
    team_members: List['TeamMember'] = field(default_factory=list)

    def __str__(self):
        members = "\n".join([str(member) for member in self.team_members])
        return f"{self.name}: {self.responsible}\n    Team Members:\n{indent(members, '        ')}"
