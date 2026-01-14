from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from src.types.common_types import IdentiyType


class BlnkBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)


# =========== Ledger DTOs ===========
class CreateLedgerRequest(BlnkBase):
    name: str
    meta_data: Optional[Dict[str, Any]] = None


class LedgerResponse(BlnkBase):
    ledger_id: str
    name: str
    created_at: datetime
    meta_data: Optional[Dict[str, Any]] = None


# =========== Balance DTOs ===========
class CreateBalanceRequest(BlnkBase):
    ledger_id: str
    identity_id: str | None = None
    currency: str


class BalanceResponse(BlnkBase):
    balance: float
    version: int
    inflight_balance: float
    credit_balance: float
    inflight_credit_balance: float
    debit_balance: float
    inflight_debit_balance: float
    precision: int
    ledger_id: str
    identity_id: str
    balance_id: str
    indicator: str
    currency: str
    created_at: datetime
    inflight_expires_at: datetime
    meta_data: Optional[Dict[str, Any]] = None
    ledger: Optional[LedgerResponse] = None


# =========== Identity DTOs ===========
class CreateIdentityRequest(BlnkBase):
    identity_type: IdentiyType
    first_name: str
    last_name: str
    other_names: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[datetime] = None
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    nationality: Optional[str] = None
    category: Optional[str] = None
    street: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    post_code: Optional[str] = None
    city: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class IdentityResponse(BlnkBase):
    identity_id: str
    identity_type: str
    organization_name: str
    category: str
    first_name: str
    last_name: str
    other_names: str
    gender: str
    email_address: str
    phone_number: str
    nationality: str
    street: str
    country: str
    state: str
    post_code: str
    city: str
    dob: datetime
    created_at: datetime
    meta_data: Optional[Dict[str, Any]] = None


class TokenizeFieldsRequest(BlnkBase):
    fields: List[str]


# =========== Transaction DTOs ===========
class Destination(BlnkBase):
    distribution: str
    identifier: str


class Source(BlnkBase):
    distribution: str
    identifier: str


class RecordTransactionRequest(BlnkBase):
    amount: float
    precise_amount: Optional[float] = None
    precision: Optional[int] = None
    reference: str
    currency: str
    source: Optional[str] = None
    destination: Optional[str] = None
    destinations: Optional[List[Destination]] = None
    sources: Optional[List[Source]] = None
    description: str
    allow_overdraft: bool = False
    skip_queue: bool = False
    inflight: bool = False
    effective_date: Optional[datetime] = None
    meta_data: Optional[Dict[str, Any]] = None


class TransactionResponse(BlnkBase):
    precise_amount: float
    amount: float
    rate: float
    precision: int
    transaction_id: str
    parent_transaction: str
    source: str
    destination: Optional[str] = None
    destinations: Optional[List[Dict[str, Any]]] = None
    reference: str
    currency: str
    description: str
    status: str
    hash: str
    allow_overdraft: bool
    inflight: bool
    created_at: datetime
    scheduled_for: datetime
    inflight_expiry_date: datetime
    meta_data: Optional[Dict[str, Any]] = None


class BulkTransactionItem(RecordTransactionRequest):
    pass


class RecordBulkTransactionRequest(BlnkBase):
    transactions: List[BulkTransactionItem]


class RefundTransactionResponse(TransactionResponse):
    pass


class UpdateInflightTransactionRequest(BlnkBase):
    status: str  # "commit" or "void"
    amount: Optional[float] = None


class SearchTransactionRequest(BlnkBase):
    q: str
    query_by: str
    filter_by: str
    group_by: str
    group_limit: int
    sort_by: str


# =========== Balance Monitor DTOs ===========
class Condition(BlnkBase):
    field: str
    operator: str
    value: float
    precision: Optional[int] = None


class CreateBalanceMonitorRequest(BlnkBase):
    balance_id: str
    condition: Condition


class BalanceMonitorResponse(BlnkBase):
    monitor_id: str
    balance_id: str
    created_at: datetime
    condition: Condition


class UpdateBalanceMonitorRequest(BlnkBase):
    balance_id: str
    description: Optional[str] = None
    condition: Condition


# =========== Reconciliation DTOs ===========
class ReconciliationUploadRequest(BlnkBase):
    file: bytes  # This might need adjustment depending on how files are handled
    source: str


class CreateReconMatchingRulesRequest(BlnkBase):
    name: str
    description: str
    criteria: List[Dict[str, Any]]


class StartReconciliationRequest(BlnkBase):
    upload_id: str
    strategy: str
    grouping_criteria: str
    matching_rule_ids: List[str]


class ExternalTransaction(BlnkBase):
    id: str
    amount: float
    reference: str
    currency: str
    description: str
    date: datetime
    source: str


class StartInstantReconciliationRequest(BlnkBase):
    external_transactions: List[ExternalTransaction]
    strategy: str
    matching_rule_ids: List[str]


# =========== Generic DTOs ===========
class PostMetadataRequest(BlnkBase):
    meta_data: Dict[str, Any]
