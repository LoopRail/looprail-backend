from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol
from uuid import UUID

from sqlmodel import Field, Relationship

from src.models.base import Base
from src.types import SupportedCurrencies, TransactionMethod, TransactionType

if TYPE_CHECKING:
    from src.models.user_model import User


class Wallet(Base, table=True):
    __tablename__ = "wallets"

    user_id: UUID = Field(foreign_key="users.id")
    user: "User" = Relationship(back_populates="wallet")
    transactions: list["Transaction"] = Relationship(back_populates="wallet")
    address: str = Field(unique=True)
    balance: str
    name: Optional[str] = Field(default=None)
    network: str
    derivation_path: Optional[str] = Field(default=None)
    provider_id: str = Field(unique=True)
    is_active: bool = Field(default=True)
    description: Optional[str] = Field(default=None)
    provider: str = Field(default="blockrader")


class Transaction(Base, table=True):
    __tablename__ = "transactions"

    wallet_id: UUID = Field(foreign_key="wallets.id")
    wallet: "Wallet" = Relationship(back_populates="transactions")
    transaction_type: TransactionType
    method: TransactionMethod
    currency: SupportedCurrencies
    sender: str
    receiver: str
    amount: str
    block_hash: Optional[str] = Field(default=None)
    block_number: Optional[int] = Field(default=None)
    transaction_hash: str = Field(unique=True)
    gas_price: Optional[str] = Field(default=None)
    gas_fee: Optional[str] = Field(default=None)
    gas_used: Optional[str] = Field(default=None)
    status: str
    note: Optional[str] = Field(default=None)
    provider_id: str = Field(unique=True)
    network: str
    chain_id: Optional[int] = Field(default=None)
    confirmations: int
    confirmed: bool
    reference: str
    reason: Optional[str] = Field(default=None)
    fee: Optional[str] = Field(default=None)


class WalletRepository(Protocol):
    """
    Protocol for a wallet repository.
    Defines the interface for interacting with wallet data.
    """

    async def create_wallet(self, *, wallet: Wallet) -> Tuple[Optional[Wallet], Error]:
        ...

    async def get_wallet_by_id(self, *, wallet_id: UUID) -> Tuple[Optional[Wallet], Error]:
        ...

    async def get_wallet_by_address(self, *, address: str) -> Tuple[Optional[Wallet], Error]:
        ...

    async def get_wallet_by_provider_id(self, *, provider_id: str) -> Tuple[Optional[Wallet], Error]:
        ...

    async def get_wallets_by_user_id(self, *, user_id: UUID) -> Tuple[list[Wallet], Error]:
        ...

    async def update_wallet(self, *, wallet: Wallet) -> Tuple[Optional[Wallet], Error]:
        ...

    async def create_transaction(self, *, transaction: Transaction) -> Tuple[Optional[Transaction], Error]:
        ...

    async def get_transaction_by_id(self, *, transaction_id: UUID) -> Tuple[Optional[Transaction], Error]:
        ...

    async def get_transactions_by_wallet_id(
        self, *, wallet_id: UUID, limit: int = 20, offset: int = 0
    ) -> Tuple[list[Transaction], Error]:
        ...

    async def get_transaction_by_hash(
        self, *, transaction_hash: str
    ) -> Tuple[Optional[Transaction], Error]:
        ...


# TODO lets sort out this gatway thing
