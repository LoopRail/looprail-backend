from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Relationship

from src.models.base import Base
from src.types.types import Gender, KYCStatus

if TYPE_CHECKING:
    from src.models.wallet_model import Wallet


class User(Base, table=True):
    __tablename__ = "users"
    __id_prefix__ = "usr_"

    first_name: Optional[str] = None
    last_name: Optional[str] = None

    email: EmailStr = Field(nullable=False, unique=True, index=True)
    username: str = Field(
        nullable=False,
        unique=True,
        index=True,
        max_length=16,
        regex=r"^[a-zA-Z0-9_-]{4,16}$",
    )

    gender: Gender = Field(nullable=False)

    is_active: bool = Field(default=True)
    is_email_verified: bool = Field(default=False)
    has_completed_onboarding: bool = Field(default=False)

    ledger_identity_id: str = Field(nullable=False, unique=True)
    onboarding_responses: List[str] = Field(
        default=[], sa_column=Column(JSONB, nullable=False, server_default="[]")
    )

    profile: "UserProfile" = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False},
    )

    credentials: "UserCredentials" = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False},
    )

    pin: "UserPin" = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False},
    )

    wallet: "Wallet" = Relationship(
        back_populates="user",
    )

    biometrics: List["UserBiometric"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    @property
    def full_name(self) -> str:
        return " ".join(filter(None, [self.first_name, self.last_name]))

    def on_delete(self):
        self.is_active = False


class UserCredentials(Base, table=True):
    __tablename__ = "user_credentials"
    __id_prefix__ = "ucr_"

    user_id: UUID = Field(
        foreign_key="users.id",
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash: str = Field(nullable=False)

    failed_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(default=None)

    user: User = Relationship(back_populates="credentials")


class UserPin(Base, table=True):
    __tablename__ = "user_pins"
    __id_prefix__ = "upn_"

    user_id: UUID = Field(
        foreign_key="users.id",
        nullable=False,
        unique=True,
        index=True,
    )

    pin_hash: str = Field(nullable=False)

    locked_until: Optional[datetime] = Field(default=None)
    last_used_at: Optional[datetime] = Field(default=None)

    user: User = Relationship(back_populates="pin")


class UserProfile(Base, table=True):
    __tablename__ = "user_profiles"
    __id_prefix__ = "usp_"

    kyc_status: KYCStatus = Field(KYCStatus.NOT_STARTED)
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    phone_number: str = Field(nullable=False, unique=True)
    date_of_birth: Optional[date] = None

    user_id: UUID = Field(foreign_key="users.id")
    user: User = Relationship(back_populates="profile")


class UserBiometric(Base, table=True):
    __tablename__ = "user_biometrics"
    __id_prefix__ = "ubm_"

    user_id: UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True,
    )
    device_id: str = Field(nullable=False, index=True)
    public_key: str = Field(nullable=False)
    is_active: bool = Field(default=True)

    user: User = Relationship(back_populates="biometrics")


# TODO Add role management for admins
