from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship

from src.models.base import Base, utc_now
from src.types.common_types import DeviceID, DeviceInfo


class Session(Base, table=True):
    __tablename__ = "sessions"
    __id_prefix__ = "ses_"

    user_id: UUID = Field(index=True)
    platform: str
    device_id: DeviceID
    ip_address: str
    user_agent: Optional[str] = Field(default=None)

    # Geolocation fields
    country: Optional[str] = Field(default=None)
    country_code: Optional[str] = Field(default=None)
    region_name: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)

    device_model: Optional[str] = Field(default=None)
    device_brand: Optional[str] = Field(default=None)
    device_manufacturer: Optional[str] = Field(default=None)
    device_name: Optional[str] = Field(default=None)
    device_product: Optional[str] = Field(default=None)
    os_version: Optional[str] = Field(default=None)
    sdk_int: Optional[int] = Field(default=None)

    allow_notifications: bool = Field(default=False)
    fcm_token: Optional[str] = Field(default=None)

    revoked_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), index=True),
    )

    last_seen_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), index=True),
    )

    passcode_hash: Optional[str] = Field(default=None)

    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="session")


class RefreshToken(Base, table=True):
    __tablename__ = "refresh_tokens"
    __id_prefix__ = "rft_"

    session_id: UUID = Field(
        foreign_key="sessions.id",
        index=True,
    )

    token_hash: str = Field(index=True)
    replaced_by_hash: Optional[str] = Field(default=None, index=True)

    revoked_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )

    expires_at: datetime = Field(
        default_factory=lambda: utc_now() + timedelta(days=30),
        sa_column=Column(DateTime(timezone=True)),
    )

    session: Optional["Session"] = Relationship(back_populates="refresh_tokens")
