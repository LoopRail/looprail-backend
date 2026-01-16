from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from src.dtos.base import Base
from src.types.common_types import AssetId, TransactionId, WalletId
from src.types.types import Currency, PaymentMethod, TransactionType


class CreateTransactionParams(BaseModel):
    wallet_id: WalletId
    transaction_type: TransactionType
    method: PaymentMethod
    currency: str
    sender: str
    receiver: str
    amount: Decimal
    status: str
    transaction_hash: str
    provider_id: str
    network: str
    confirmations: int
    confirmed: bool
    reference: str
    block_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_price: Optional[str] = None
    gas_fee: Optional[str] = None
    gas_used: Optional[str] = None
    note: Optional[str] = None
    chain_id: Optional[int] = None
    reason: Optional[str] = None
    fee: Optional[Decimal] = None


class TransactionRead(Base):
    model_config = ConfigDict(from_attributes=True)

    id: TransactionId
    wallet_id: WalletId
    asset_id: AssetId
    transaction_type: TransactionType
    method: PaymentMethod
    currency: Currency
    sender: str
    receiver: str
    amount: Decimal
    status: str
    transaction_hash: str
    provider_id: str
    network: str
    confirmations: int
    confirmed: bool
    reference: str
    block_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_price: Optional[str] = None
    gas_fee: Optional[str] = None
    gas_used: Optional[str] = None
    note: Optional[str] = None
    chain_id: Optional[int] = None
    reason: Optional[str] = None
    fee: Optional[Decimal] = None


class TransactionReadList(Base):
    transactions: List[TransactionRead]

