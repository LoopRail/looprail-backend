from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Union


from src.dtos.transaction_dtos import CreateTransactionParams, CryptoTransactionParams


from src.types.blockrader import DepositSuccessData, WithdrawSuccessData
from src.types.country_types import CountriesData
from src.types.types import PaymentMethod, TransactionType
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

    return CryptoTransactionParams(
        wallet_id=wallet.id,
        asset_id=asset_id,
        transaction_type=transaction_type,
        payment_type=transaction_type,
        method=PaymentMethod.BLOCKCHAIN,  # Assuming, as PaymentMethod doesn't have crypto
        currency=event_data.currency.lower(),
        sender=event_data.senderAddress,
        receiver=event_data.recipientAddress,
        amount=Decimal(event_data.amount),
        status=event_data.status,
        transaction_hash=event_data.hash or "pending",
        provider_id=event_data.id,
        network=event_data.network,
        confirmations=event_data.confirmations,
        confirmed=event_data.confirmed,
        reference=event_data.reference,
        block_hash=event_data.blockHash,
        block_number=event_data.blockNumber,
        gas_price=event_data.gasPrice,
        gas_fee=event_data.gasFee,
        gas_used=event_data.gasUsed,
        note=event_data.note,
        chain_id=event_data.chainId,
        reason=reason if reason is not None else event_data.reason,
        fee=fee
        if fee is not None
        else (Decimal(event_data.fee) if event_data.fee else None),
        country=country,
    )
