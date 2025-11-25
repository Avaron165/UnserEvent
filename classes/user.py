from dataclasses import dataclass
from classes.created_modified_mixin import CreatedModifiedMixin
from classes.person import Person

@dataclass(kw_only=True)
class User(Person, CreatedModifiedMixin):
    username: str

    def __str__(self):
        return f"({self.username}) {Person.__str__(self)}"