from decimal import Decimal
from typing import Union

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import TransactionRepository
from src.models import Wallet
from src.models.wallet_model import Transaction
from src.types import PaymentMethod, TransactionType
from src.types.blockrader import (
    DepositSuccessData,
    WithdrawCancelledData,
    WithdrawFailedData,
    WithdrawSuccessData,
)

logger = get_logger(__name__)


class TransactionUsecase:
    def __init__(self, transaction_repo: TransactionRepository):
        self._transaction_repo = transaction_repo

    async def create_from_deposit(
        self,
        event_data: DepositSuccessData,
        wallet: Wallet,
    ):
        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type=TransactionType.CREDIT,
            method=PaymentMethod.WALLET_TRANSFER,  # Assuming, as PaymentMethod doesn't have crypto
            currency=event_data.currency,
            sender=event_data.senderAddress,
            receiver=event_data.recipientAddress,
            amount=Decimal(event_data.amount),
            status=event_data.status.value,
            transaction_hash=event_data.hash,
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
            reason=event_data.reason,
            fee=Decimal(event_data.fee) if event_data.fee else None,
        )
        _, err = await self._transaction_repo.create_transaction(
            transaction=transaction
        )
        if err:
            logger.error(
                "Failed to create transaction record for event %s: %s",
                event_data.id,
                err.message,
            )

    async def create_from_withdrawal(
        self,
        event_data: WithdrawSuccessData,
        wallet: Wallet,
    ):
        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type=TransactionType.DEBIT,
            method=PaymentMethod.WALLET_TRANSFER,  # Assuming, as PaymentMethod doesn't have crypto
            currency=event_data.currency,
            sender=event_data.senderAddress,
            receiver=event_data.recipientAddress,
            amount=Decimal(event_data.amount),
            status=event_data.status.value,
            transaction_hash=event_data.hash,
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
            reason=event_data.reason,
            fee=Decimal(event_data.fee) if event_data.fee else None,
        )
        _, err = await self._transaction_repo.create_transaction(
            transaction=transaction
        )
        if err:
            logger.error(
                "Failed to create transaction record for event %s: %s",
                event_data.id,
                err.message,
            )

    async def update_status_from_event(
        self, event_data: Union[WithdrawFailedData, WithdrawCancelledData]
    ):
        transaction, err = await self._transaction_repo.get_transaction_by_provider_id(
            provider_id=event_data.id
        )
        if err:
            logger.error(
                "Transaction with provider_id %s not found: %s",
                event_data.id,
                err.message,
            )
            return

        transaction.status = event_data.status.value
        transaction.reason = event_data.reason

        _, err = await self._transaction_repo.update_transaction(
            transaction=transaction
        )
        if err:
            logger.error(
                "Failed to update transaction status for event %s: %s",
                event_data.id,
                err.message,
            )
