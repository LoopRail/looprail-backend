from decimal import Decimal
from typing import List, Optional, Tuple, Union

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
        logger.debug("TransactionUsecase initialized.")

    async def create_transaction(self, params: CreateTransactionParams) -> Error:
        logger.debug("Creating transaction with reference: %s", params.reference)
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
        logger.info("Transaction record created for reference: %s", params.reference)
        return None

    async def get_transactions_by_wallet_id(
        self, *, wallet_id: WalletId, limit: int = 20, offset: int = 0
    ) -> Tuple[List[Transaction], Error]:
        logger.debug(
            "Getting transactions for wallet %s with limit %s and offset %s",
            wallet_id,
            limit,
            offset,
        )
        transactions, err = await self._transaction_repo.get_transactions_by_wallet_id(
            wallet_id=wallet_id, limit=limit, offset=offset
        )
        if err:
            logger.error(
                "Failed to get transactions for wallet %s: %s", wallet_id, err.message
            )
            return [], err
        logger.debug(
            "Retrieved %s transactions for wallet %s", len(transactions), wallet_id
        )
        return transactions, err

    async def get_transaction_by_id(
        self, *, transaction_id: TransactionId
    ) -> Tuple[Transaction, Error]:
        logger.debug("Getting transaction with ID: %s", transaction_id)
        transaction, err = await self._transaction_repo.get_transaction_by_id(
            transaction_id=transaction_id
        )
        if err:
            logger.debug("Transaction %s not found: %s", transaction_id, err.message)
            return None, err
        logger.debug("Transaction %s retrieved.", transaction_id)
        return transaction, err

    async def update_status_from_event(
        self, event_data: Union[WithdrawFailedData, WithdrawCancelledData]
    ) -> Error:
        logger.debug(
            "Updating transaction status from event for provider ID: %s", event_data.id
        )
        transaction, err = await self._transaction_repo.get_transaction_by_provider_id(
            provider_id=event_data.id
        )
        if err:
            logger.error(
                "Transaction with provider_id %s not found for status update: %s",
                event_data.id,
                err.message,
            )
            return err
        logger.debug(
            "Transaction %s found for provider ID %s.", transaction.id, event_data.id
        )

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
        logger.info(
            "Transaction %s status updated to %s from event.",
            transaction.id,
            event_data.status.value,
        )
        return None

    async def update_transaction_status(
        self,
        *,
        transaction_id: TransactionId,
        new_status: str,
        message: Optional[str] = None,
    ) -> Optional[Error]:
        logger.debug(
            "Updating status of transaction %s to %s with message: %s",
            transaction_id,
            new_status,
            message,
        )
        transaction, err = await self._transaction_repo.get_transaction_by_id(
            transaction_id=transaction_id
        )
        if err:
            logger.error(
                "Transaction with ID %s not found for status update: %s",
                transaction_id,
                err.message,
            )
            return err
        logger.debug("Transaction %s found for status update.", transaction_id)

        transaction.status = new_status
        if message:
            transaction.reason = message

        _, err = await self._transaction_repo.update_transaction(
            transaction=transaction
        )
        if err:
            logger.error(
                "Failed to update transaction status for ID %s to %s: %s",
                transaction_id,
                new_status,
                err.message,
            )
            return err
        logger.info("Transaction %s status updated to %s.", transaction_id, new_status)
        return None

    async def update_transaction_fee(
        self, *, transaction_id: TransactionId, fee: Decimal
    ) -> Optional[Error]:
        logger.debug("Updating fee for transaction %s to %s", transaction_id, fee)
        transaction, err = await self._transaction_repo.get_transaction_by_id(
            transaction_id=transaction_id
        )
        if err:
            logger.error(
                "Transaction with ID %s not found for fee update: %s",
                transaction_id,
                err.message,
            )
            return err
        logger.debug("Transaction %s found for fee update.", transaction_id)

        transaction.fee = fee

        _, err = await self._transaction_repo.update_transaction(
            transaction=transaction
        )
        if err:
            logger.error(
                "Failed to update transaction fee for ID %s to %s: %s",
                transaction_id,
                fee,
                err.message,
            )
            return err
        logger.info("Transaction %s fee updated to %s.", transaction_id, fee)
        return None
