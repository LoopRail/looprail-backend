from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.dtos.user_dtos import UserPublic


class SessionData(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    user: UserPublic
    device_id: str
    device_type: str | None = None
    ip_address: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime

    @classmethod
    def new_session(
        cls,
        user: UserPublic,
        device_id: str,
        ip_address: str,
        device_type: str | None = None,
        expires_in_days: int = 30,
    ) -> "SessionData":
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        return cls(
            user=user,
            device_id=device_id,
            device_type=device_type,
            ip_address=ip_address,
            expires_at=expires_at,
        )

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
