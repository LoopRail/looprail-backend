from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional, Protocol
from uuid import UUID

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

from src.models.base import Base
from src.types import KYCStatus

if TYPE_CHECKING:
    from src.models.wallet_model import Wallet


class Address(SQLModel):
    """Represents a user's address."""

    street: str
    city: str
    state: str
    postal_code: str
    country: str


class User(Base):
    __tablename__ = "users"

    first_name: str
    last_name: str
    email: EmailStr = Field(unique=True)
    username: str = Field(max_length=15, unique=True)
    is_active: bool = Field(default=False)

    profile: "UserProfile" = Relationship(back_populates="user")
    wallet: Wallet = Relationship(back_populates="user")

    def full_name(self) -> str:
        """Returns the user's full name if first and last names are set."""
        return f"{self.first_name} {self.last_name}"

    def fmt_date_of_birth(self) -> str:
        return self.date_of_birth.strftime("%d/%m/%y")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    kyc_status: KYCStatus = Field(KYCStatus.NOT_STARTED)
    is_email_verified: bool = Field(default=False)
    address: Address
    phone_number: str
    date_of_birth: date

    user_id: UUID = Field(foreign_key="users.id")
    user: "User" = Relationship(back_populates="profile")


class UserRepository(Protocol):
    """
    Protocol for a user repository.
    Defines the interface for interacting with user data.
    """

    def create_user(self, user: User) -> None: ...

    def get_by_username(self, username: str) -> Optional[User]: ...

    def get_by_email(self, email: str) -> Optional[User]: ...

    def list_all(self) -> list[User]: ...


# Add role management for admins
