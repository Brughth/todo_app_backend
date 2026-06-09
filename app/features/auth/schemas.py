import uuid
from datetime import datetime
from pydantic import BaseModel


class Auth(BaseModel):
    """Response schema."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    # TODO: add response fields


class AuthCreate(BaseModel):
    """Payload for creating a Auth."""
    # TODO: add create fields
    pass


class AuthUpdate(BaseModel):
    """Payload for updating a Auth — all fields optional."""
    # TODO: add update fields (all Optional)
    pass
