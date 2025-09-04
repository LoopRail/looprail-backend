from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from sqlmodel import Field, Relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.user_model import User


class Wallet(Base):
    user_id: UUID = Field(foreign_key="users.id")
    user: User = Relationship(back_populates="wallet")
    transactions: list["Transactions"] = Relationship(back_populates="wallet")
    address: str = Field(unique=True)
    balance: str


class Transactions(Base):
    pass


class WalletRepository(Protocol):
    """
    Protocol for a wallet repository.
    Defines the interface for interacting with wallet data.
    """


# TODO lets sort out this gatway thing
