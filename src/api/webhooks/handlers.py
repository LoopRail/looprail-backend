from rq import Queue

from src.api.webhooks.registry import register
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.redis import RQManager
from src.infrastructure.repositories import AssetRepository, WalletRepository
from src.infrastructure.services import LedgerService, LockService
from src.types import NotFoundError, WorldLedger
from src.types.blnk import RecordTransactionRequest, UpdateInflightTransactionRequest
from src.types.blockrader import (
    WebhookDepositSuccess,
    WebhookDepositSweptSuccess,
    WebhookEventType,
    WebhookWithdrawCancelled,
    WebhookWithdrawFailed,
    WebhookWithdrawSuccess,
)
from src.types.common_types import WalletId
from src.types.types import TransactionStatus
from src.usecases import TransactionUsecase

logger = get_logger(__name__)


@register(event_type=WebhookEventType.DEPOSIT_SWEPT_SUCCESS)
async def handle_deposit_swept_success(
    event: WebhookDepositSweptSuccess,
    rq_manager: RQManager = None,
    **kwargs,
):
    logger.info("Enqueuing deposit swept success event: %s", event.data.id)
    if rq_manager:
        deposit_queue = Queue("deposits", connection=rq_manager.get_connection())
        # Model dump to ensure serializable data
        deposit_queue.enqueue(
            "services.deposits.tasks.process_deposit_swept_success_task",
            event.model_dump(),
        )


@register(event_type=WebhookEventType.DEPOSIT_SUCCESS)
async def handle_deposit_success(
    event: WebhookDepositSuccess,
    rq_manager: RQManager = None,
    **kwargs,
):
    logger.info("Enqueuing deposit success event: %s", event.data.id)
    if rq_manager:
        deposit_queue = Queue("deposits", connection=rq_manager.get_connection())
        # Model dump to ensure serializable data
        deposit_queue.enqueue(
            "services.deposits.tasks.process_deposit_success_task",
            event.model_dump(),
        )


@register(event_type=WebhookEventType.WITHDRAW_SUCCESS)
async def handle_withdraw_success(
    event: WebhookWithdrawSuccess,
    ledger_service: LedgerService,
    transaction_usecase: TransactionUsecase,
    lock_service: LockService,
    **kwargs,
):
    logger.info("Handling withdraw success event: %s", event.data.id)

    lock = lock_service.get("withdrawals")
    lock_id, err = await lock.acquire(event.data.hash)
    if err:
        logger.error(err)
        return

    txn_type = None
    if event.data.metadata and isinstance(event.data.metadata, dict):
        txn_type = event.data.metadata.get("type")

    logger.debug("Looking up local transaction by reference %s", event.data.reference)
    txn, err = await transaction_usecase.repo.find_one(reference=event.data.reference)
    if err or not txn:
        logger.error(
            "Transaction with reference %s not found for event %s: %s",
            event.data.reference,
            event.data.id,
            err.message if err else "not found",
        )
        await lock.release(event.data.hash, lock_id)
        return

    if event.data.hash:
        txn.transaction_hash = event.data.hash

    if txn_type != "bank":
        if txn.ledger_transaction_id:
            _, ledger_err = await ledger_service.transactions.update_inflight_transaction(
                txn.ledger_transaction_id,
                UpdateInflightTransactionRequest(status="commit"),
            )
            if ledger_err:
                logger.error(
                    "Failed to commit inflight ledger transaction %s for event %s: %s",
                    txn.ledger_transaction_id,
                    event.data.id,
                    ledger_err.message,
                )
        txn.status = TransactionStatus.COMPLETED
        logger.info("Local transaction %s marked as COMPLETED for event %s", txn.id, event.data.id)
    else:
        logger.info("Local transaction %s (bank transfer) status NOT updated via webhook", txn.id)

    await transaction_usecase.repo.update(txn)

    err = await lock.release(event.data.hash, lock_id)
    if err:
        logger.error(err)
        return

    logger.info(
        "Withdrawal success event %s processed successfully.",
        event.data.id,
    )
    return


@register(event_type=WebhookEventType.WITHDRAW_FAILED)
async def handle_withdraw_failed(
    event: WebhookWithdrawFailed,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    asset_repo: AssetRepository,
    transaction_usecase: TransactionUsecase,
    **kwargs,
):
    logger.info("Handling withdraw failed event: %s", event.data.id)
    logger.debug(
        "Attempting to update local transaction status for event %s", event.data.id
    )
    err = await transaction_usecase.update_status_from_event(event.data)
    if err:
        logger.error(
            "Failed to update local transaction status for event %s: %s",
            event.data.id,
            err.message,
        )
        return
    logger.info(
        "Local transaction status updated to failed for event %s", event.data.id
    )

    # Use metadata for wallet lookup if available
    wallet_id = None
    if event.data.metadata and isinstance(event.data.metadata, dict):
        wallet_id = event.data.metadata.get("wallet_id")
        if wallet_id:
            wallet_id = WalletId(wallet_id).clean()

    if wallet_id:
        wallet, err = await wallet_repo.get(wallet_id)
    else:
        wallet, err = await wallet_repo.get_wallet_by_address(
            address=event.data.senderAddress
        )

    if err:
        logger.error(
            "Wallet lookup failed for withdrawal failed event %s: %s",
            event.data.id,
            err.message,
        )
        return
    logger.debug("Wallet found: %s", wallet.get_prefixed_id())

    asset, err = await asset_repo.find_one(
        wallet_id=wallet.id, asset_id=event.data.asset.asset_id
    )
    if err:
        logger.error(
            "Asset %s not found for wallet %s: %s",
            event.data.asset.asset_id,
            wallet.get_prefixed_id(),
            err.message,
        )
        return

    if not asset.ledger_balance_id:
        logger.error(
            "Asset %s has no ledger balance ID for wallet %s",
            asset.asset_id,
            wallet.get_prefixed_id(),
        )
        return

    transaction_request = RecordTransactionRequest(
        amount=0,
        reference=event.data.id,
        currency=event.data.currency,
        source=asset.ledger_balance_id,
        destination=WorldLedger.WORLD_OUT,
        description=f"Failed withdrawal to {event.data.recipientAddress}. Reason: {event.data.reason}",
    )
    logger.debug("Recording failed transaction on ledger for event %s", event.data.id)
    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record failed withdrawal transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )
        return
    logger.info(
        "Failed withdrawal transaction successfully recorded on ledger for event %s",
        event.data.id,
    )
    return


@register(event_type=WebhookEventType.WITHDRAW_CANCELLED)
async def handle_withdraw_cancelled(
    event: WebhookWithdrawCancelled,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    asset_repo: AssetRepository,
    transaction_usecase: TransactionUsecase,
    **kwargs,
):
    logger.info("Handling withdraw cancelled event: %s", event.data.id)
    logger.debug(
        "Attempting to update local transaction status for event %s", event.data.id
    )
    err = await transaction_usecase.update_status_from_event(event.data)
    if err:
        logger.error(
            "Failed to update local transaction status for event %s: %s",
            event.data.id,
            err.message,
        )
        return
    logger.info(
        "Local transaction status updated to cancelled for event %s", event.data.id
    )

    # Use metadata for wallet lookup if available
    wallet_id = None
    if event.data.metadata and isinstance(event.data.metadata, dict):
        wallet_id = event.data.metadata.get("wallet_id")
        if wallet_id:
            wallet_id = WalletId(wallet_id).clean()

    if wallet_id:
        wallet, err = await wallet_repo.get(wallet_id)
    else:
        wallet, err = await wallet_repo.get_wallet_by_address(
            address=event.data.senderAddress
        )

    if err:
        logger.error(
            "Wallet lookup failed for withdrawal cancelled event %s: %s",
            event.data.id,
            err.message,
        )
        return
    logger.debug("Wallet found: %s", wallet.get_prefixed_id())

    asset, err = await asset_repo.find_one(
        wallet_id=wallet.id, asset_id=event.data.asset.asset_id
    )
    if err:
        logger.error(
            "Asset %s not found for wallet %s: %s",
            event.data.asset.asset_id,
            wallet.get_prefixed_id(),
            err.message,
        )
        return

    if not asset.ledger_balance_id:
        logger.error(
            "Asset %s has no ledger balance ID for wallet %s",
            asset.asset_id,
            wallet.get_prefixed_id(),
        )
        return

    transaction_request = RecordTransactionRequest(
        amount=0,
        reference=event.data.id,
        currency=event.data.currency,
        source=asset.ledger_balance_id,
        destination=WorldLedger.WORLD_OUT,
        description=f"Cancelled withdrawal to {event.data.recipientAddress}. Reason: {event.data.reason}",
    )
    logger.debug(
        "Recording cancelled transaction on ledger for event %s", event.data.id
    )
    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record cancelled withdrawal transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )
        return
    logger.info(
        "Cancelled withdrawal transaction successfully recorded on ledger for event %s",
        event.data.id,
    )
