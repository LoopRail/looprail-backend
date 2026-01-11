from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from src.models.base import Base
from src.types.types import (
    AssetType,
    Currency,
    PaymentMethod,
    TokenStandard,
    TransactionType,
)
from src.types.common_types import Address, Chain

if TYPE_CHECKING:
    from src.models.user_model import User

# TODO we need to creat tairs and then add limits to tht rairs and stuff


class Wallet(Base, table=True):
    __tablename__ = "wallets"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    address: Address = Field(unique=True, index=True, nullable=False)
    chain: Chain = Field(nullable=False)
    provider: str = Field(index=True, nullable=False)
    ledger_id: str = Field(index=True, nullable=False)
    is_active: bool = Field(default=True, nullable=False)

    name: Optional[str] = Field(default=None)
    derivation_path: Optional[str] = Field(default=None)
    user: "User" = Relationship(back_populates="wallet")

    transactions: List["Transaction"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    assets: List["Asset"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"passive_deletes": True},
    )


class Asset(Base, table=True):
    __tablename__ = "assets"

    wallet_id: Optional[UUID] = Field(
        default=None,
        foreign_key="wallets.id",
        index=True,
    )
    ledger_balance_id: str = Field(default=None, nullable=False, unique=True)
    name: str = Field(nullable=False)
    asset_id: AssetType = Field(unique=True, index=True, nullable=False)
    address: Address = Field(nullable=False)
    symbol: str = Field(nullable=False)
    decimals: int = Field(nullable=False)
    address: Address = Field(nullable=False)
    network: str = Field(nullable=False)
    standard: Optional[TokenStandard] = Field(default=None)
    is_active: bool = Field(default=True, nullable=False)

    wallet: Optional["Wallet"] = Relationship(
        back_populates="assets",
        sa_relationship_kwargs={"passive_deletes": True},
    )


class Transaction(Base, table=True):
    __tablename__ = "transactions"

    wallet_id: Optional[UUID] = Field(
        default=None,
        foreign_key="wallets.id",
        index=True,
    )
    transaction_type: TransactionType = Field(nullable=False)
    method: PaymentMethod = Field(nullable=False)
    currency: Currency = Field(nullable=False)
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

    wallet: Optional["Wallet"] = Relationship(back_populates="transactions")
