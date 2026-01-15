from typing import List, Tuple, Union

from src.dtos import CreateTransactionParams
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import TransactionRepository
from src.models import Transaction
from src.types import Error
from src.types.blockrader import WithdrawCancelledData, WithdrawFailedData
from src.types.common_types import TransactionId, WalletId

logger = get_logger(__name__)


class TransactionUsecase:
    def __init__(self, transaction_repo: TransactionRepository):
        self._transaction_repo = transaction_repo

    async def create_transaction(self, params: CreateTransactionParams) -> Error:
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
            return err
        return None

    async def get_transactions_by_wallet_id(
        self, *, wallet_id: WalletId, limit: int = 20, offset: int = 0
    ) -> Tuple[List[Transaction], Error]:
        return await self._transaction_repo.get_transactions_by_wallet_id(
            wallet_id=wallet_id, limit=limit, offset=offset
        )

    async def get_transaction_by_id(
        self, *, transaction_id: TransactionId
    ) -> Tuple[Transaction, Error]:
        return await self._transaction_repo.get_transaction_by_id(
            transaction_id=transaction_id
        )

    async def update_status_from_event(
        self, event_data: Union[WithdrawFailedData, WithdrawCancelledData]
    ) -> Error:
        transaction, err = await self._transaction_repo.get_transaction_by_provider_id(
            provider_id=event_data.id
        )
        if err:
            logger.error(
                "Transaction with provider_id %s not found: %s",
                event_data.id,
                err.message,
            )
            return err

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
            return err
        return None
