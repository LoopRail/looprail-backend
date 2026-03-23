from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Relationship

from src.models.base import Base
from src.types.common_types import Address, Network, ReferenceId
from src.types.types import (
    Currency,
    DepositStage,
    PaymentMethod,
    TransactionStatus,
    TransactionType,
    PaycrestOrderStatus,
)
from src.utils.app_utils import generate_transaction_reference

if TYPE_CHECKING:
    from src.models.wallet_model import Asset, Wallet


class Transaction(Base, table=True):
    __tablename__ = "transactions"
    __id_prefix__ = "txn_"

    # Core fields
    wallet_id: UUID = Field(
        foreign_key="wallets.id",
        index=True,
    )
    asset_id: UUID = Field(
        foreign_key="assets.id",
        index=True,
    )

    # Transaction classification
    transaction_type: TransactionType = Field(
        nullable=False, sa_column_kwargs={"index": True}
    )
    payment_type: TransactionType = Field(
        nullable=False, sa_column_kwargs={"index": True}
    )
    method: PaymentMethod = Field(nullable=False)
    currency: Currency = Field(nullable=False)
    country: Optional[str] = Field(default=None, sa_column_kwargs={"index": True})

    # Parties
    sender: str = Field(nullable=False)
    receiver: str = Field(nullable=False)

    # Amounts
    amount: Decimal = Field(nullable=False)
    fee: Optional[Decimal] = Field(default=None)

    # Status tracking
    status: TransactionStatus = Field(
        nullable=False,
        default=TransactionStatus.PENDING,
        index=True,
    )

    # References
    reference: ReferenceId = Field(
        nullable=False,
        unique=True,
        default_factory=generate_transaction_reference,
        index=True,
    )
    external_reference: Optional[str] = Field(default=None, index=True)

    ledger_transaction_id: Optional[str] = Field(default=None, unique=True)

    transaction_hash: Optional[str] = Field(default=None, unique=True, index=True)
    network: Optional[Network] = Field(default=None)
    confirmations: int = Field(nullable=False, default=0)
    confirmed: bool = Field(nullable=False, default=False)
    block_hash: Optional[str] = Field(default=None)
    block_number: Optional[int] = Field(default=None)
    gas_price: Optional[str] = Field(default=None)
    gas_fee: Optional[str] = Field(default=None)
    gas_used: Optional[str] = Field(default=None)
    chain_id: Optional[int] = Field(default=None)
    session_id: Optional[UUID] = Field(nullable=True, default=None)

    # General fields
    narration: Optional[str] = Field(default=None, max_length=500)

    destination_data: dict = Field(
        default={}, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )

    meta_data: dict = Field(
        default={}, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )

    error_message: Optional[str] = Field(default=None)

    asset: "Asset" = Relationship(back_populates="transactions")
    wallet: "Wallet" = Relationship(back_populates="transactions")

    # Detail relationships (if you want to add strict detail tables later)
    bank_transfer: Optional["BankTransferDetail"] = Relationship(
        back_populates="transaction",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )
    wallet_transfer: Optional["WalletTransferDetail"] = Relationship(
        back_populates="transaction",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )
    internal_transfer: Optional["InternalTransferDetail"] = Relationship(
        back_populates="transaction",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )
    deposit: Optional["DepositDetail"] = Relationship(
        back_populates="transaction",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )


class BankTransferDetail(Base, table=True):
    """Strict schema for bank transfer details"""

    __tablename__ = "bank_transfer_details"
    __id_prefix__ = "btd_"

    transaction_id: UUID = Field(
        foreign_key="transactions.id", unique=True, nullable=False, ondelete="CASCADE"
    )

    # Bank account details
    bank_code: str = Field(nullable=False, index=True, max_length=20)
    bank_name: str = Field(nullable=False, max_length=100)
    account_number: str = Field(nullable=False, index=True, max_length=20)
    account_name: str = Field(nullable=False, max_length=200)

    # Verification
    account_verified: bool = Field(default=False)
    verification_date: Optional[datetime] = Field(default=None)

    # Provider details
    provider: str = Field(default="paycrest", max_length=50)
    provider_reference: Optional[str] = Field(default=None, index=True)
    paycrest_txn_id: Optional[str] = Field(default=None, index=True)
    paycrest_status: Optional[PaycrestOrderStatus] = Field(default=None)

    # Conversion rate (Asset per 1 Unit of Withdrawal Currency)
    rate: Optional[Decimal] = Field(default=None)

    # Relationship
    transaction: Transaction = Relationship(back_populates="bank_transfer")


class WalletTransferDetail(Base, table=True):
    """Strict schema for external wallet/crypto transfer details"""

    __tablename__ = "wallet_transfer_details"
    __id_prefix__ = "wtd_"

    transaction_id: UUID = Field(
        foreign_key="transactions.id", unique=True, nullable=False, ondelete="CASCADE"
    )

    # Wallet details
    wallet_address: Address = Field(nullable=False, index=True, max_length=200)
    network: Network = Field(nullable=False)
    memo: Optional[str] = Field(default=None, max_length=100)

    # Blockchain tracking (additional to main transaction table)
    address_verified: bool = Field(default=False)
    contract_address: Optional[str] = Field(default=None)

    # Relationship
    transaction: Transaction = Relationship(back_populates="wallet_transfer")


class InternalTransferDetail(Base, table=True):
    """Details specific to internal user-to-user transfers"""

    __tablename__ = "internal_transfer_details"
    __id_prefix__ = "itd_"

    transaction_id: UUID = Field(
        foreign_key="transactions.id", unique=True, nullable=False, ondelete="CASCADE"
    )

    # Recipient details
    recipient_user_id: str = Field(nullable=False, index=True)
    recipient_asset_id: str = Field(nullable=False)
    transfer_type: str = Field(default="p2p", max_length=20)

    # Relationship
    transaction: Transaction = Relationship(back_populates="internal_transfer")


class DepositDetail(Base, table=True):
    """Details specific to deposits (bank or blockchain)"""

    __tablename__ = "deposit_details"
    __id_prefix__ = "dpd_"

    transaction_id: UUID = Field(
        foreign_key="transactions.id", unique=True, nullable=False, ondelete="CASCADE"
    )

    # Deposit source
    source_type: str = Field(nullable=True, max_length=50)  # bank, chain
    source_reference: Optional[str] = Field(default=None, index=True)

    # Stage tracking (moved from main Transaction table)
    deposit_stage: DepositStage = Field(
        nullable=False,
        default=DepositStage.PENDING,
        index=True,
    )

    # Provider info
    provider: str = Field(nullable=True, max_length=50)
    provider_reference: Optional[str] = Field(default=None, index=True)

    # Relationship
    transaction: Transaction = Relationship(back_populates="deposit")
