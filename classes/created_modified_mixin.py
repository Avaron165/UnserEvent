from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from user import User

def utcnow():
    return datetime.now(timezone.utc)

@dataclass(kw_only=True)
class CreatedModifiedMixin:
    created_at: datetime = field(default_factory=utcnow)
    modified_at: Optional[datetime] = None
    created_by: Optional['User'] = field(default=None, repr=False, compare=False)
    modified_by: Optional['User'] = field(default=None, repr=False, compare=False)
