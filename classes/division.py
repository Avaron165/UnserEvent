from dataclasses import dataclass, field
from uuid import UUID
from classes.uuid_utils import new_id
from typing import Optional, List
from classes.person import Person
from textwrap import indent

@dataclass(kw_only=True)
class Division:
    name: str
    sub_divisions: List['Division'] = field(default_factory=list)
    parent_division: Optional['Division'] = None
    description: Optional[str] = None
    id: UUID = field(default_factory=new_id)
    persons: List['Person'] = field(default_factory=list)

    def __str__(self):
        sub_lines = "\n".join([str(sub) for sub in self.sub_divisions])
        return (f"{self.name}, "
                f"    description={self.description}\n"
                f"    Subdivisions:\n{indent(sub_lines,"        ")}")