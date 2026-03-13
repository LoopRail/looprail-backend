from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Union

from src.dtos.transaction_dtos import (
    CreateTransactionParams,
    DepositParams,
    WalletTransferParams,
)
from src.types.blockrader import DepositSuccessData, WithdrawSuccessData
from src.types.country_types import CountriesData
from src.types.types import DepositStage, TransactionStatus, TransactionType
from src.utils.country_utils import get_country_name_by_currency

if TYPE_CHECKING:
    from src.models import Wallet


def create_transaction_params_from_event(
    event_data: Union[DepositSuccessData, WithdrawSuccessData],
    wallet: Wallet,
    asset_id: str,
    transaction_type: TransactionType,
    countries: Optional[CountriesData] = None,
    country: Optional[str] = None,
    fee: Optional[Decimal] = None,
    reason: Optional[str] = None,
) -> CreateTransactionParams:
    if country is None and countries is not None:
        country = get_country_name_by_currency(countries, event_data.currency)

    session_id = None
    if event_data.metadata and isinstance(event_data.metadata, dict):
        session_id = event_data.metadata.get("session_id")

    base_kwargs = {
        "user_id": wallet.user_id,
        "wallet_id": wallet.id,
        "amount": Decimal(event_data.amount),
        "currency": event_data.currency.lower(),
        "asset_id": asset_id,
        "transaction_type": transaction_type,
        "transaction_hash": event_data.hash or "pending",
        "status": TransactionStatus.COMPLETED,
        "reference": event_data.reference,
        "narration": f"{transaction_type.value.capitalize()} of {event_data.amount} {event_data.currency}",
        "country": country,
        "fee": fee if fee is not None else (Decimal(event_data.fee) if event_data.fee else None),
        "reason": reason if reason is not None else event_data.reason,
        "session_id": session_id,
    }

    if transaction_type == TransactionType.CREDIT:
        return DepositParams(
            **base_kwargs,
            deposit_stage=DepositStage.RECEIVED,
            source_type="blockchain",
            source_reference=event_data.senderAddress,
            provider="blockradar",
        )

    return WalletTransferParams(
        **base_kwargs,
        address=event_data.recipientAddress,
        network=wallet.network,
    )
