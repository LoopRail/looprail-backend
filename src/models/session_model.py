from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from src.models.base import Base


class Session(Base, table=True):
    __tablename__ = "sessions"
    __id_prefix__ = "ses_"
    user_id: UUID = Field(index=True)
    platform: str
    device_id: str
    ip_address: str
    revoked_at: Optional[datetime] = Field(default=None, index=True)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    refresh_tokens: list["RefreshToken"] = Relationship(back_populates="session")


class RefreshToken(Base, table=True):
    __tablename__ = "refresh_tokens"
    __id_prefix__ = "rft_"
    session_id: UUID = Field(foreign_key="sessions.id", index=True)
    token_hash: str = Field(index=True)
    replaced_by_hash: Optional[str] = Field(default=None, index=True)
    revoked_at: Optional[datetime] = Field(default=None, index=True)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=30)
    )
    session: Optional[Session] = Relationship(back_populates="refresh_tokens")
