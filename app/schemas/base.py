from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    """Mixin for created_at/modified_at fields."""

    created_at: datetime
    modified_at: Optional[datetime] = None


class AuditMixin(TimestampMixin):
    """Mixin for full audit fields including created_by/modified_by."""

    created_by_id: Optional[UUID] = None
    modified_by_id: Optional[UUID] = None
