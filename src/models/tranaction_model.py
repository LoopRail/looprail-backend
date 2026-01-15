from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from src.models.base import Base
from src.types.types import Currency, PaymentMethod, TransactionType

if TYPE_CHECKING:
    from src.models.wallet_model import Asset, Wallet


class Transaction(Base, table=True):
    __tablename__ = "transactions"
    __id_prefix__ = "txn_"

    wallet_id: UUID = Field(
        foreign_key="wallets.id",
        index=True,
    )
    asset_id: UUID = Field(
        foreign_key="assets.id",
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
    note: Optional[str] = Field(
        default=None
    )  # TODO we need only one resona or not as narration
    chain_id: Optional[int] = Field(default=None)
    reason: Optional[str] = Field(default=None)
    fee: Optional[Decimal] = Field(default=None)

    asset: "Asset" = Relationship(back_populates="transactions")
    wallet: "Wallet" = Relationship(back_populates="transactions")
