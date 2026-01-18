from decimal import Decimal
from typing import List, Optional, Tuple, Union

from src.dtos import (
    BankTransferParams,
    CreateTransactionParams,
    CryptoTransactionParams,
)
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import TransactionRepository
from src.models import BankTransferDetail, Transaction, WalletTransferDetail
from src.types import Error, TransactionStatus, error
from src.types.blockrader import WithdrawCancelledData, WithdrawFailedData
from src.types.common_types import TransactionId, WalletId
from src.types.types import TransactionType

logger = get_logger(__name__)


class TransactionUsecase:
    def __init__(self, transaction_repo: TransactionRepository):
        self._transaction_repo = transaction_repo
        logger.debug("TransactionUsecase initialized.")

    async def create_transaction(
        self,
        params: CreateTransactionParams,
    ) -> tuple[Optional[Transaction], Optional[Error]]:
        """
        Create a transaction with type-specific handling
        """
        logger.debug("Creating transaction of type: %s", params.transaction_type)

        # Step 1: Create the main transaction record
        transaction_data = self._prepare_transaction_data(params)
        transaction = Transaction(**transaction_data)

        created_txn, err = await self._transaction_repo.create_transaction(
            transaction=transaction
        )
        if err:
            logger.error("Failed to create transaction: %s", err.message)
            return None, err

        logger.info("Transaction created with ID: %s", created_txn.id)

        # Step 2: Create type-specific detail record
        detail_err = await self._create_transaction_details(params, created_txn.id)
        if detail_err:
            logger.error("Failed to create transaction details: %s", detail_err.message)
            await self._transaction_repo.update_status(
                created_txn.id, TransactionStatus.FAILED
            )
            return None, detail_err

        return created_txn, None

    def _prepare_transaction_data(
        self,
        params: CreateTransactionParams,
    ) -> dict:
        """
        Prepare transaction data based on param type
        """
        base_data = {
            "wallet_id": params.wallet_id,
            "asset_id": params.asset_id,
            "transaction_type": params.transaction_type,
            "method": params.method,
            "currency": params.currency,
            "sender": params.sender,
            "receiver": params.receiver,
            "amount": params.amount,
            "note": params.narration,
            "fee": params.fee,
            "status": TransactionStatus.PENDING,
            "metadata": params.metadata,
        }

        # Add type-specific fields
        if isinstance(params, CryptoTransactionParams):
            base_data.update(
                {
                    "transaction_hash": params.transaction_hash,
                    "network": params.network,
                    "block_hash": params.block_hash,
                    "block_number": params.block_number,
                    "gas_price": params.gas_price,
                    "gas_fee": params.gas_fee,
                    "gas_used": params.gas_used,
                    "chain_id": params.chain_id,
                    "confirmations": params.confirmations,
                    "destination_data": {
                        "wallet_address": params.destination_wallet_address,
                        "memo": params.memo,
                    }
                    if params.destination_wallet_address
                    else {},
                }
            )

        elif isinstance(params, BankTransferParams):
            base_data.update(
                {
                    "external_reference": params.external_reference,
                    "destination_data": {
                        "bank_code": params.bank_code,
                        "bank_name": params.bank_name,
                        "account_number": params.account_number,
                        "account_name": params.account_name,
                        "provider": params.provider,
                    },
                }
            )

        return base_data

    async def _create_transaction_details(
        self,
        params: CreateTransactionParams,
        transaction_id: TransactionId,
    ) -> Optional[Error]:
        """
        Create type-specific detail records
        """
        try:
            if isinstance(params, BankTransferParams):
                return await self._create_bank_transfer_detail(params, transaction_id)

            if (
                isinstance(params, CryptoTransactionParams)
                and params.destination_wallet_address
            ):
                return await self._create_wallet_transfer_detail(params, transaction_id)

            return None

        except Exception as e:
            logger.error("Error creating transaction details: %s", str(e))
            return error(f"Failed to create transaction details: {str(e)}")

    async def _create_bank_transfer_detail(
        self, params: BankTransferParams, transaction_id: TransactionId
    ) -> Optional[Error]:
        """Create bank transfer detail record"""

        detail = BankTransferDetail(
            transaction_id=transaction_id,
            bank_code=params.bank_code,
            bank_name=params.bank_name,
            account_number=params.account_number,
            account_name=params.account_name,
            provider=params.provider,
            session_id=params.session_id,
            provider_reference=params.external_reference,
        )

        _, err = await self._transaction_repo.create(detail)
        return err

    async def _create_wallet_transfer_detail(
        self, params: CryptoTransactionParams, transaction_id: TransactionId
    ) -> Optional[Error]:
        """Create wallet transfer detail record"""
        detail = WalletTransferDetail(
            transaction_id=transaction_id,
            wallet_address=params.destination_wallet_address,
            network=params.network,
            memo=params.memo,
        )

        _, err = await self._transaction_repo.create(detail)
        return err

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
