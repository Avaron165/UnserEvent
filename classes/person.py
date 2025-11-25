from dataclasses import dataclass, field
from classes.created_modified_mixin import CreatedModifiedMixin
from typing import Optional
from uuid import UUID
from classes.uuid_utils import new_id
from classes.participant import Participant



@dataclass(kw_only=True)
class Person(Participant, CreatedModifiedMixin):
    id: UUID = field(default_factory=new_id)
    lastname: str
    firstname: str
    email: Optional[str] = None
    mobile: Optional[str] = None

    def __str__(self):
        return f"{self.firstname} {self.lastname}: {self.id}, email={self.email if self.email else 'N/A'}, mobile = {self.mobile if self.mobile else 'N/A'}"