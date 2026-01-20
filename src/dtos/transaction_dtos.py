from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Union
from uuid import UUID

from pydantic import (BaseModel, ConfigDict, Field, computed_field,
                      field_validator)
from pydantic_extra_types.country import CountryShortName

from src.dtos.base import Base
from src.models.tranaction_model import Transaction
from src.types.common_types import (Address, AssetId, TransactionId, UserId,
                                    WalletId)
from src.types.types import (Currency, PaymentMethod, TransactionStatus,
                             TransactionType)


class BaseTransactionParams(Base):
    """Base params for all transaction types"""

    wallet_id: UUID
    asset_id: UUID
    transaction_type: TransactionType
    payment_type: TransactionType
    method: PaymentMethod
    currency: Currency
    sender: UserId | Address
    receiver: str
    amount: Decimal = Field(gt=0)
    narration: Optional[str] = Field(default=None, max_length=500)
    fee: Optional[Decimal] = Field(default=None, ge=0)
    metadata: dict = Field(default_factory=dict)
    country: Optional[CountryShortName] = Field(default=None)


class CryptoTransactionParams(BaseTransactionParams):
    """Params specific to crypto/blockchain transactions"""

    transaction_hash: str = Field(min_length=1)
    network: str = Field(min_length=1)

    # Optional blockchain fields
    block_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_price: Optional[str] = None
    gas_fee: Optional[str] = None
    gas_used: Optional[str] = None
    chain_id: Optional[int] = None
    confirmations: int = Field(default=0, ge=0)

    # Wallet-specific details
    destination_wallet_address: Optional[str] = None
    memo: Optional[str] = None


class BankTransferParams(BaseTransactionParams):
    """Params specific to bank transfers"""

    bank_code: str = Field(min_length=3, max_length=20)
    bank_name: str = Field(min_length=1, max_length=100)
    account_number: str = Field(min_length=10, max_length=20)
    account_name: str = Field(min_length=1, max_length=200)

    # Provider info
    provider: str = Field(default="paycrest")
    session_id: Optional[str] = None
    external_reference: Optional[str] = None

    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("-", "")
        if not cleaned.isdigit():
            raise ValueError("Account number must contain only digits")
        return cleaned


#
# class InternalTransferParams(BaseTransactionParams):
#     """Params for internal user-to-user transfers"""
#
#     recipient_user_id: UserId
#     recipient_wallet_id: WalletId
#     recipient_asset_id: AssetId
#     transfer_type: str = Field(default="p2p")
#

CreateTransactionParams = CryptoTransactionParams | BankTransferParams


class TransactionRead(Base):
    """Base transaction response with common fields"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Core fields
    id: TransactionId
    wallet_id: WalletId = Field(alias="wallet-id")
    asset_id: AssetId = Field(alias="asset-id")

    # Transaction info
    transaction_type: TransactionType = Field(alias="transaction-type")
    payment_type: TransactionType = Field(alias="payment-type")
    method: PaymentMethod
    currency: Currency
    status: TransactionStatus
    country: Optional[CountryShortName] = None

    # Parties
    sender: str
    receiver: str

    # Amounts
    amount: Decimal
    fee: Optional[Decimal] = None

    # References
    reference: str
    external_reference: Optional[str] = Field(default=None, alias="external-reference")

    # General
    narration: Optional[str] = None
    note: Optional[str] = None  # Keeping for backward compatibility

    # Timestamps
    created_at: datetime = Field(alias="created-at")
    updated_at: Optional[datetime] = Field(default=None, alias="updated-at")
    completed_at: Optional[datetime] = Field(default=None, alias="completed-at")

    # Blockchain fields (optional - only for crypto transactions)
    transaction_hash: Optional[str] = Field(default=None, alias="transaction-hash")
    network: Optional[str] = None
    confirmations: Optional[int] = Field(default=0)
    confirmed: Optional[bool] = Field(default=False)
    block_hash: Optional[str] = Field(default=None, alias="block-hash")
    block_number: Optional[int] = Field(default=None, alias="block-number")
    gas_price: Optional[str] = Field(default=None, alias="gas-price")
    gas_fee: Optional[str] = Field(default=None, alias="gas-fee")
    gas_used: Optional[str] = Field(default=None, alias="gas-used")
    chain_id: Optional[int] = Field(default=None, alias="chain-id")

    # Destination data (type-specific details stored as dict)
    destination: Optional[dict] = None

    # Metadata
    metadata: Optional[dict] = Field(default_factory=dict)

    # Error tracking
    error_code: Optional[str] = Field(default=None, alias="error-code")
    error_message: Optional[str] = Field(default=None, alias="error-message")

    @computed_field
    @property
    def is_crypto(self) -> bool:
        """Check if this is a crypto transaction"""
        return self.method == PaymentMethod.BLOCKCHAIN

    @computed_field
    @property
    def is_bank_transfer(self) -> bool:
        """Check if this is a bank transfer"""
        return self.method == PaymentMethod.BANK_TRANSFER


# ============================================================================
# LIST RESPONSES
# ============================================================================


class TransactionReadList(Base):
    """List of transactions"""

    transactions: List[TransactionRead]
    total: Optional[int] = None
    page: Optional[int] = None
    page_size: Optional[int] = Field(default=None, alias="page-size")

    model_config = ConfigDict(populate_by_name=True)


# ============================================================================
# DETAILED TRANSACTION RESPONSE (with related data)
# ============================================================================


class BankTransferDetailRead(BaseModel):
    """Bank transfer detail information"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    bank_code: str = Field(alias="bank-code")
    bank_name: str = Field(alias="bank-name")
    account_number: str = Field(alias="account-number")
    account_name: str = Field(alias="account-name")
    provider: str
    session_id: Optional[str] = Field(default=None, alias="session-id")
    account_verified: bool = Field(default=False, alias="account-verified")


class WalletTransferDetailRead(BaseModel):
    """Wallet transfer detail information"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    wallet_address: str = Field(alias="wallet-address")
    network: str
    memo: Optional[str] = None
    address_verified: bool = Field(default=False, alias="address-verified")
    contract_address: Optional[str] = Field(default=None, alias="contract-address")


class TransactionDetailRead(TransactionRead):
    """Transaction with full detail information"""

    # Type-specific details (only one will be populated based on transaction type)
    bank_transfer_detail: Optional[BankTransferDetailRead] = Field(
        default=None, alias="bank-transfer-detail"
    )
    wallet_transfer_detail: Optional[WalletTransferDetailRead] = Field(
        default=None, alias="wallet-transfer-detail"
    )


# ============================================================================
# CONVERSION HELPER
# ============================================================================


class TransactionResponseBuilder:
    """Helper to build proper transaction responses from DB models"""

    @staticmethod
    def from_transaction(
        transaction: "Transaction", include_details: bool = False
    ) -> Union[TransactionRead, TransactionDetailRead]:
        """
        Convert Transaction model to response model
        Automatically populates destination data from detail tables or destination_data field
        """

        # Build base response data
        base_data = {
            "id": transaction.id,
            "wallet_id": transaction.wallet_id,
            "asset_id": transaction.asset_id,
            "transaction_type": transaction.transaction_type,
            "payment_type": transaction.payment_type,
            "method": transaction.method,
            "currency": transaction.currency,
            "status": transaction.status,
            "country": transaction.country,
            "sender": transaction.sender,
            "receiver": transaction.receiver,
            "amount": transaction.amount,
            "fee": transaction.fee,
            "reference": transaction.reference,
            "external_reference": getattr(transaction, "external_reference", None),
            "narration": getattr(transaction, "narration", None) or transaction.note,
            "note": transaction.note,
            "created_at": transaction.created_at,
            "updated_at": getattr(transaction, "updated_at", None),
            "completed_at": getattr(transaction, "completed_at", None),
            "metadata": getattr(transaction, "metadata", {}),
            "error_code": getattr(transaction, "error_code", None),
            "error_message": getattr(transaction, "error_message", None),
        }

        # Add blockchain fields if present
        if transaction.transaction_hash:
            base_data.update(
                {
                    "transaction_hash": transaction.transaction_hash,
                    "network": transaction.network,
                    "confirmations": transaction.confirmations,
                    "block_hash": transaction.block_hash,
                    "block_number": transaction.block_number,
                    "gas_price": transaction.gas_price,
                    "gas_fee": transaction.gas_fee,
                    "gas_used": transaction.gas_used,
                    "chain_id": transaction.chain_id,
                }
            )

        # Build destination from detail tables or destination_data
        destination = TransactionResponseBuilder._build_destination(transaction)
        base_data["destination"] = destination

        # Return detailed response if requested
        if include_details:
            detail_data = base_data.copy()

            # Add bank transfer detail if present
            if hasattr(transaction, "bank_transfer") and transaction.bank_transfer:
                detail_data["bank_transfer_detail"] = (
                    BankTransferDetailRead.model_validate(transaction.bank_transfer)
                )

            # Add wallet transfer detail if present
            if hasattr(transaction, "wallet_transfer") and transaction.wallet_transfer:
                detail_data["wallet_transfer_detail"] = (
                    WalletTransferDetailRead.model_validate(transaction.wallet_transfer)
                )

            return TransactionDetailRead(**detail_data)

        return TransactionRead(**base_data)

    @staticmethod
    def _build_destination(transaction: "Transaction") -> Optional[dict]:
        """Build destination dict from detail tables or destination_data field"""

        # Try to get from detail tables first (more structured)
        if hasattr(transaction, "bank_transfer") and transaction.bank_transfer:
            bt = transaction.bank_transfer
            return {
                "bank-code": bt.bank_code,
                "bank-name": bt.bank_name,
                "account-number": bt.account_number,
                "account-name": bt.account_name,
                "provider": bt.provider,
            }

        if hasattr(transaction, "wallet_transfer") and transaction.wallet_transfer:
            wt = transaction.wallet_transfer
            return {
                "wallet-address": wt.wallet_address,
                "network": wt.network,
                "memo": wt.memo,
            }

        if hasattr(transaction, "internal_transfer") and transaction.internal_transfer:
            it = transaction.internal_transfer
            return {
                "recipient-user-id": it.recipient_user_id,
                "recipient-asset-id": it.recipient_asset_id,
                "transfer-type": it.transfer_type,
            }

        # Fallback to destination_data field
        if hasattr(transaction, "destination_data") and transaction.destination_data:
            return transaction.destination_data

        return None

    @staticmethod
    def from_transaction_list(
        transactions: List["Transaction"],
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> TransactionReadList:
        """Convert list of transactions to response"""
        return TransactionReadList(
            transactions=[
                TransactionResponseBuilder.from_transaction(txn) for txn in transactions
            ],
            total=len(transactions),
            page=page,
            page_size=page_size,
        )
