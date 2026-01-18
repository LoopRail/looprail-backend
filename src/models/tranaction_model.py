from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Relationship

from src.models.base import Base
from src.types.common_types import ReferenceId, UserId
from src.types.types import Currency, PaymentMethod, TransactionStatus, TransactionType
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
    method: PaymentMethod = Field(nullable=False)
    currency: Currency = Field(nullable=False)

    # Parties
    sender: UserId = Field(nullable=False)
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
    external_reference: Optional[str] = Field(
        default=None, index=True
    )  # Bank/provider reference

    # Blockchain fields (for crypto transactions)
    transaction_hash: Optional[str] = Field(default=None, unique=True, index=True)
    network: Optional[str] = Field(default=None)
    confirmations: int = Field(nullable=False, default=0)
    confirmed: bool = Field(nullable=False, default=False)
    block_hash: Optional[str] = Field(default=None)
    block_number: Optional[int] = Field(default=None)
    gas_price: Optional[str] = Field(default=None)
    gas_fee: Optional[str] = Field(default=None)
    gas_used: Optional[str] = Field(default=None)
    chain_id: Optional[int] = Field(default=None)

    # General fields
    narration: Optional[str] = Field(default=None, max_length=500)  # Alias for note

    # Destination details - store type-specific data here
    destination_data: dict = Field(
        default={}, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )

    # Metadata for additional flexible data
    extra_data: dict = Field(
        default={}, sa_column=Column(JSONB, nullable=False, server_default="{}")
    )

    # Relationships
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
    session_id: Optional[str] = Field(default=None)
    provider_reference: Optional[str] = Field(default=None, index=True)

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
    wallet_address: str = Field(nullable=False, index=True, max_length=200)
    network: str = Field(nullable=False, max_length=50)
    memo: Optional[str] = Field(default=None, max_length=100)

    # Blockchain tracking (additional to main transaction table)
    address_verified: bool = Field(default=False)
    contract_address: Optional[str] = Field(default=None)

    # Relationship
    transaction: Transaction = Relationship(back_populates="wallet_transfer")


#
# class InternalTransferDetail(Base):
#     """Details specific to internal user-to-user transfers"""
#     __tablename__ = "internal_transfer_details"
#
#     id = Column(String, primary_key=True)
#     transaction_id = Column(String, ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False)
#
#     # Recipient details
#     recipient_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
#     recipient_asset_id = Column(String, ForeignKey("assets.id"), nullable=False)
#     recipient_transaction_id = Column(String, nullable=True)  # The matching credit transaction
#
#     # Transfer metadata
#     transfer_type = Column(String, default="p2p")  # p2p, gift, payment, etc.
#
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#
#     transaction = relationship("Transaction", back_populates="internal_transfer")
#     recipient_user = relationship("User", foreign_keys=[recipient_user_id])
#
#     __table_args__ = (
#         Index('idx_recipient_user', 'recipient_user_id'),
#     )
#
#
# class DepositDetail(Base):
#     """Details specific to deposits (bank or card)"""
#     __tablename__ = "deposit_details"
#
#     id = Column(String, primary_key=True)
#     transaction_id = Column(String, ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False)
#
#     # Deposit source
#     source_type = Column(String, nullable=False)  # bank, card
#     source_reference = Column(String, index=True)  # Bank reference or card token
#
#     # Bank deposit details
#     source_bank_code = Column(String, nullable=True)
#     source_account_number = Column(String, nullable=True)
#     source_account_name = Column(String, nullable=True)
#
#     # Card deposit details
#     card_last4 = Column(String(4), nullable=True)
#     card_brand = Column(String, nullable=True)  # visa, mastercard, verve
#     card_exp = Column(String, nullable=True)
#
#     # Payment provider info
#     provider = Column(String, nullable=False)  # paystack, flutterwave, etc.
#     provider_reference = Column(String, index=True)
#     authorization_code = Column(String, nullable=True)  # For recurring payments
#
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#
#     transaction = relationship("Transaction", back_populates="deposit_detail")
#
#     __table_args__ = (
#         Index('idx_provider_ref', 'provider', 'provider_reference'),
#     )
