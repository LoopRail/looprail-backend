from typing import Union

from src.dtos import CreateTransactionParams
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import TransactionRepository
from src.models.wallet_model import Transaction
from src.types.blockrader import (
    WithdrawCancelledData,
    WithdrawFailedData,
)

logger = get_logger(__name__)


class TransactionUsecase:
    def __init__(self, transaction_repo: TransactionRepository):
        self._transaction_repo = transaction_repo

    async def create_transaction(self, params: CreateTransactionParams):
        transaction = Transaction(**params.model_dump())
        _, err = await self._transaction_repo.create_transaction(
            transaction=transaction
        )
        if err:
            logger.error(
                "Failed to create transaction record for reference %s: %s",
                params.reference,
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
