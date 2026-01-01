from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LockedAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    locked_at: datetime = Field(default_factory=lambda: datetime.utcnow().isoformat())
