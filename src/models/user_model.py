from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import EmailStr
from sqlmodel import Field, Relationship

from src.models.base import Base
from src.types.types import Gender, KYCStatus

if TYPE_CHECKING:
    from src.models.wallet_model import Wallet


class User(Base, table=True):
    __tablename__ = "users"
    __id_prefix__ = "usr_"

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr = Field(unique=True)
    gender: Gender = Field(nullable=False)
    password_hash: str = Field(nullable=False)
    username: str = Field(
        nullable=False,
        max_length=16,
        min_length=4,
        unique=True,
        regex=r"^[a-zA-Z0-9_-]{4,16}$",
    )
    salt: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    ledger_identiy_id: str = Field(nullable=False, unique=True)
    is_email_verified: bool = Field(default=False)
    has_completed_onboarding: bool = Field(default=False)
    transaction_pin: Optional[str] = Field(default=None)

    profile: UserProfile = Relationship(back_populates="user")
    wallet: Wallet = Relationship(back_populates="user")

    @property
    def full_name(self) -> str:
        """Returns the user's full name if first and last names are set."""
        return f"{self.first_name} {self.last_name}"

    def on_delete(self):
        self.is_active = False


class UserProfile(Base, table=True):
    __tablename__ = "user_profiles"
    __id_prefix__ = "usp_"

    kyc_status: KYCStatus = Field(KYCStatus.NOT_STARTED)
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone_number: str
    date_of_birth: date
    # links: Optional[List[HttpUrl]] = Field(default_factory=list)

    user_id: UUID = Field(foreign_key="users.id")
    user: User = Relationship(back_populates="profile")


# TODO Add role management for admins
