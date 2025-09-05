from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Protocol, Tuple
from uuid import UUID

from sqlmodel import Field, Relationship

from src.models.base import Base
from src.types import Error, SupportedCurrencies, TransactionMethod, TransactionType

if TYPE_CHECKING:
    from src.models.user_model import User

from decimal import Decimal


class Wallet(Base, table=True):
    __tablename__ = "wallets"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    address: str = Field(unique=True, index=True, nullable=False)
    balance: Decimal = Field(default=Decimal("0.00"), nullable=False)
    network: str = Field(nullable=False)
    usdc_asset_id: UUID = Field(nullable=False)
    provider_id: str = Field(unique=True, index=True, nullable=False)
    provider: str = Field(default="blockrader", nullable=False)
    is_active: bool = Field(default=True, nullable=False)

    name: Optional[str] = Field(default=None)
    derivation_path: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)

    user: "User" = Relationship(back_populates="wallet")
    transactions: list["Transaction"] = Relationship(back_populates="wallet")


class Transaction(Base, table=True):
    __tablename__ = "transactions"

    wallet_id: UUID = Field(foreign_key="wallets.id", index=True)
    transaction_type: TransactionType = Field(nullable=False)
    method: TransactionMethod = Field(nullable=False)
    currency: SupportedCurrencies = Field(nullable=False)
    sender: str = Field(nullable=False)
    receiver: str = Field(nullable=False)
    amount: Decimal = Field(nullable=False)
    status: str = Field(nullable=False)
    transaction_hash: str = Field(unique=True, index=True, nullable=False)
    provider_id: str = Field(unique=True, index=True, nullable=False)
    network: str = Field(nullable=False)
    confirmations: int = Field(nullable=False)
    confirmed: bool = Field(nullable=False)
    reference: str = Field(nullable=False)

    block_hash: Optional[str] = Field(default=None)
    block_number: Optional[int] = Field(default=None)
    gas_price: Optional[str] = Field(default=None)
    gas_fee: Optional[str] = Field(default=None)
    gas_used: Optional[str] = Field(default=None)
    note: Optional[str] = Field(default=None)
    chain_id: Optional[int] = Field(default=None)
    reason: Optional[str] = Field(default=None)
    fee: Optional[Decimal] = Field(default=None)

    wallet: "Wallet" = Relationship(back_populates="transactions")


class WalletRepository(Protocol):
    """
    Protocol for a wallet repository.
    Defines the interface for interacting with wallet data.
    """

    async def create_wallet(
        self, *, wallet: Wallet
    ) -> Tuple[Optional[Wallet], Error]: ...

    async def get_wallet_by_id(
        self, *, wallet_id: UUID
    ) -> Tuple[Optional[Wallet], Error]: ...

    async def get_wallet_by_address(
        self, *, address: str
    ) -> Tuple[Optional[Wallet], Error]: ...

    async def get_wallet_by_provider_id(
        self, *, provider_id: str
    ) -> Tuple[Optional[Wallet], Error]: ...

    async def get_wallets_by_user_id(
        self, *, user_id: UUID
    ) -> Tuple[list[Wallet], Error]: ...

    async def update_wallet(
        self, *, wallet: Wallet
    ) -> Tuple[Optional[Wallet], Error]: ...

    async def create_transaction(
        self, *, transaction: Transaction
    ) -> Tuple[Optional[Transaction], Error]: ...

    async def get_transaction_by_id(
        self, *, transaction_id: UUID
    ) -> Tuple[Optional[Transaction], Error]: ...

    async def get_transactions_by_wallet_id(
        self, *, wallet_id: UUID, limit: int = 20, offset: int = 0
    ) -> Tuple[list[Transaction], Error]: ...

    async def get_transaction_by_hash(
        self, *, transaction_hash: str
    ) -> Tuple[Optional[Transaction], Error]: ...
