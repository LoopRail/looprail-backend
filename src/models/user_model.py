from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional, Protocol, Tuple
from uuid import UUID

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

from src.models.base import Base
from src.types import Error, KYCStatus

if TYPE_CHECKING:
    from src.models.wallet_model import Wallet


class User(Base, table=True):
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


class UserProfile(Base, table=True):
    __tablename__ = "user_profiles"

    kyc_status: KYCStatus = Field(KYCStatus.NOT_STARTED)
    is_email_verified: bool = Field(default=False)
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone_number: str
    date_of_birth: date

    user_id: UUID = Field(foreign_key="users.id")
    user: "User" = Relationship(back_populates="profile")


class UserRepository(Protocol):
    """
    Protocol for a user repository.
    Defines the interface for interacting with user data.
    """

    # User methods
    async def create_user(self, *, user: User) -> Tuple[Optional[User], Error]: ...

    async def get_user_by_id(
        self, *, user_id: UUID
    ) -> Tuple[Optional[User], Error]: ...

    async def get_user_by_username(
        self, *, username: str
    ) -> Tuple[Optional[User], Error]: ...

    async def get_user_by_email(
        self, *, email: EmailStr
    ) -> Tuple[Optional[User], Error]: ...

    async def list_users(
        self, *, limit: int = 50, offset: int = 0
    ) -> Tuple[list[User], Error]: ...

    async def update_user(self, *, user: User) -> Tuple[Optional[User], Error]: ...

    async def delete_user(self, *, user_id: UUID) -> Error: ...

    # UserProfile methods
    async def create_user_profile(
        self, *, user_profile: UserProfile
    ) -> Tuple[Optional[UserProfile], Error]: ...

    async def get_user_profile_by_user_id(
        self, *, user_id: UUID
    ) -> Tuple[Optional[UserProfile], Error]: ...

    async def update_user_profile(
        self, *, user_profile: UserProfile
    ) -> Tuple[Optional[UserProfile], Error]: ...


# Add role management for admins
