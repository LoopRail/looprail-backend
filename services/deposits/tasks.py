import asyncio
from typing import Any, Dict

from src.infrastructure.logger import get_logger
from services.deposits.dependencies import get_task_dependencies_factory
from src.types.blockrader import WebhookDepositSweptSuccess, WebhookDepositSuccess
from src.types import (
    DepositStage,
    NotFoundError,
    TransactionStatus,
    TransactionType,
    WorldLedger,
)
from src.types.blnk.dtos import (
    RecordTransactionRequest,
    UpdateInflightTransactionRequest,
)
from src.types.notification_types import NotificationAction
from src.utils.email_helpers import send_transactional_email
from src.utils.notification_helpers import enqueue_notifications_for_user
from src.utils.transaction_utils import create_transaction_params_from_event

logger = get_logger(__name__)

# Max retries for the swept task while waiting for RECEIVED stage
MAX_DEPOSIT_SWEPT_RETRIES = 5
# Delay (seconds) between each retry within the held lock
DEPOSIT_SWEPT_RETRY_DELAY_SECONDS = 10


async def _process_deposit_swept_success_task_async(event_data: Dict[str, Any]):
    event = WebhookDepositSweptSuccess.model_validate(event_data)

    async with get_task_dependencies_factory() as factory:
        ledger_service = factory.ledger_service
        transaction_repo = factory.transaction_repository
        config = factory.config
        lock_service = factory.lock_service
        session_repo = factory.session_repository
        notification_usecase = factory.notification_usecase
        user_repo = factory.user_repository
        resend_service = factory.resend_service

        logger.info("Handling deposit swept success event task: %s", event.data.id)

        # --- Acquire lock (blocking up to 30s to queue behind deposit_success) ---
        logger.debug(
            "Acquiring deposit lock for hash %s (event %s)",
            event.data.hash,
            event.data.id,
        )
        lock = lock_service.get("deposits")
        lock_id, err = await lock.acquire(event.data.hash, blocking_timeout_seconds=30)
        if err:
            logger.error(
                "Could not acquire lock for swept event %s hash %s: %s",
                event.data.id,
                event.data.hash,
                err,
            )
            return

        # --- While holding the lock, check stage from Redis cache (not DB) ---
        for attempt in range(1, MAX_DEPOSIT_SWEPT_RETRIES + 1):
            stage, stage_err = await lock.get_state(event.data.hash)

            if stage == DepositStage.RECEIVED:
                logger.info(
                    "[attempt %d/%d] Swept event %s: Redis cache shows stage=RECEIVED. Proceeding.",
                    attempt,
                    MAX_DEPOSIT_SWEPT_RETRIES,
                    event.data.id,
                )
                break

            if attempt < MAX_DEPOSIT_SWEPT_RETRIES:
                logger.warning(
                    "[attempt %d/%d] Swept event %s: stage is '%s' (expected RECEIVED). "
                    "Waiting %ds before retry...",
                    attempt,
                    MAX_DEPOSIT_SWEPT_RETRIES,
                    event.data.id,
                    stage or "not set",
                    DEPOSIT_SWEPT_RETRY_DELAY_SECONDS,
                )
                await asyncio.sleep(DEPOSIT_SWEPT_RETRY_DELAY_SECONDS)
            else:
                logger.error(
                    "Swept event %s: stage is still '%s' after %d attempts. "
                    "Releasing lock and giving up.",
                    event.data.id,
                    stage or "not set",
                    MAX_DEPOSIT_SWEPT_RETRIES,
                )
                await lock.release(event.data.hash, lock_id)
                return

        # --- Fetch transaction from DB (only once, now that stage is RECEIVED) ---
        txn, err = await transaction_repo.find_one(
            external_reference=event.data.reference, load=["wallet"]
        )
        if err or txn is None:
            logger.error(
                "Swept event %s: transaction with reference %s not found: %s",
                event.data.id,
                event.data.reference,
                err,
            )
            await lock.release(event.data.hash, lock_id)
            return

        # Already fully processed — no need to commit again
        if txn.status == TransactionStatus.COMPLETED:
            logger.info(
                "Swept event %s: transaction %s is already COMPLETED. Skipping.",
                event.data.id,
                txn.get_prefixed_id(),
            )
            await lock.release(event.data.hash, lock_id)
            return

        # --- Validate amount ---
        try:
            float(event.data.amount)
        except (ValueError, TypeError):
            logger.error(
                "Invalid amount format: %s for event %s",
                event.data.amount,
                event.data.id,
            )
            await lock.release(event.data.hash, lock_id)
            return

        # --- Verify source wallet + asset ---
        source_wallet, err = config.block_rader.wallets.get_wallet(
            wallet_id=event.data.wallet.wallet_id
        )
        if err:
            logger.error(
                "Source wallet not found for address %s: %s",
                event.data.recipientAddress,
                err.message,
            )
            await lock.release(event.data.hash, lock_id)
            return
        logger.debug("Source wallet found: %s", source_wallet.wallet_name)

        source_asset, err = source_wallet.get(asset_id=event.data.asset.asset_id)
        if err:
            logger.error(
                "Swept asset with ID %s not found in source wallet %s",
                event.data.asset.asset_id,
                source_wallet.wallet_name,
            )
            await lock.release(event.data.hash, lock_id)
            return
        logger.debug("Processing swept transaction for asset %s", source_asset.name)

        # --- Commit inflight ledger transaction ---
        transaction_request = UpdateInflightTransactionRequest(status="commit")
        logger.debug("Recording transaction on ledger for event %s", event.data.id)
        _, err = await ledger_service.transactions.update_inflight_transaction(
            txn.ledger_transaction_id, transaction_request
        )
        if err:
            logger.error(
                "Failed to commit deposit swept transaction on ledger for event %s: %s",
                event.data.id,
                err.message,
            )
            await lock.release(event.data.hash, lock_id)
            return

        # --- Update DB: COMPLETED + SWEPT stage ---
        # Fetch again with deposit relationship
        txn, err = await transaction_repo.find_one(id=txn.id, load_relationships=["deposit"])

        txn.status = TransactionStatus.COMPLETED
        if txn.deposit:
            txn.deposit.deposit_stage = DepositStage.SWEPT
            await transaction_repo.update(txn.deposit)
        else:
            logger.warning("No DepositDetail found for transaction %s", txn.id)

        _, err = await transaction_repo.update(txn)
        if err:
            logger.error(
                "Failed to update transaction %s to COMPLETED/SWEPT for event %s: %s",
                txn.get_prefixed_id(),
                event.data.id,
                err.message,
            )
            await lock.release(event.data.hash, lock_id)
            return

        # --- Update Redis cache to SWEPT ---
        cache_err = await lock.set_state(event.data.hash, DepositStage.SWEPT)
        if cache_err:
            logger.warning(
                "Failed to update Redis cache to SWEPT for hash %s: %s",
                event.data.hash,
                cache_err,
            )

        # --- Release lock ---
        err = await lock.release(event.data.hash, lock_id)
        if err:
            logger.error(err)
            return

        logger.info(
            "Deposit swept transaction committed for event %s. Stage=SWEPT.",
            event.data.id,
        )

        # --- Notify user ---
        if session_repo and notification_usecase and txn:
            await enqueue_notifications_for_user(
                user_id=str(txn.wallet.user_id),
                session_repo=session_repo,
                notification_usecase=notification_usecase,
                title="Deposit Confirmed ✅",
                body=f"Your deposit of {event.data.amount} {event.data.currency} has been confirmed and added to your wallet.",
                action=NotificationAction.DEPOSIT_CONFIRMED,
                data={"transaction_id": str(txn.id)},
            )

        if user_repo and resend_service and txn:
            user, _ = await user_repo.find_one(id=txn.wallet.user_id)
            if user:
                await send_transactional_email(
                    resend_service=resend_service,
                    to=user.email,
                    subject="Your Deposit Has Been Confirmed",
                    template_name="deposit_confirmed",
                    app_logo_url=config.app.full_logo_url or config.app.logo_url,
                    amount=event.data.amount,
                    currency=event.data.currency,
                    transaction_id=str(txn.id),
                )



async def _process_deposit_success_task_async(event_data: Dict[str, Any]):
    event = WebhookDepositSuccess.model_validate(event_data)

    async with get_task_dependencies_factory() as factory:
        ledger_service = factory.ledger_service
        wallet_repo = factory.wallet_repository
        asset_repo = factory.asset_repository
        lock_service = factory.lock_service
        transaction_usecase = factory.transaction_usecase
        config = factory.config

        logger.info("Handling deposit success event task: %s", event.data.id)
        logger.debug(
            "Acquiring deposit lock for hash %s (event %s)",
            event.data.hash,
            event.data.id,
        )
        lock = lock_service.get("deposits")
        lock_id, err = await lock.acquire(event.data.hash, blocking_timeout_seconds=30)
        if err:
            logger.error(
                "Could not acquire lock for deposit event %s hash %s: %s",
                event.data.id,
                event.data.hash,
                err,
            )
            return

        # --- Idempotency check: already processed? ---
        txn, err = await transaction_usecase.repo.find_one(
            transaction_hash=event.data.hash
        )
        if err and err != NotFoundError:
            logger.error(err)
            await lock.release(event.data.hash, lock_id)
            return
        if txn:
            if txn.status == TransactionStatus.COMPLETED:
                logger.info(
                    "Deposit event %s: transaction %s is already COMPLETED. Skipping.",
                    event.data.id,
                    txn.get_prefixed_id(),
                )
            else:
                logger.info(
                    "Deposit event %s: transaction hash %s already exists (ID %s, stage %s). Skipping.",
                    event.data.id,
                    event.data.hash,
                    txn.id,
                    txn.deposit_stage,
                )
            await lock.release(event.data.hash, lock_id)
            return

        # --- Resolve wallet, asset, and create local transaction record ---
        source_wallet, err = config.block_rader.wallets.get_wallet(
            wallet_id=event.data.wallet.wallet_id
        )
        if err:
            logger.error(
                "Source wallet not found for address %s: %s",
                event.data.recipientAddress,
                err.message,
            )
            await lock.release(event.data.hash, lock_id)
            return
        logger.debug("Source wallet found: %s", source_wallet.wallet_name)

        source_asset, err = source_wallet.get(asset_id=event.data.asset.asset_id)
        if err:
            logger.error(
                "Asset with ID %s not found in wallet %s",
                event.data.asset.asset_id,
                source_wallet.wallet_name,
            )
            await lock.release(event.data.hash, lock_id)
            return
        logger.debug("Processing transaction for asset %s", source_asset.name)

        wallet, err = await wallet_repo.get_wallet_by_address(
            address=event.data.recipientAddress
        )
        if err:
            logger.error(
                "Wallet not found for address %s: %s",
                event.data.recipientAddress,
                err.message,
            )
            await lock.release(event.data.hash, lock_id)
            return
        logger.debug("Wallet found: %s", wallet.get_prefixed_id())

        asset, err = await asset_repo.find_one(
            wallet_id=wallet.id, asset_id=source_asset.asset_id
        )
        if err:
            logger.error(
                "Asset %s not found for wallet %s: %s",
                source_asset.asset_id,
                wallet.get_prefixed_id(),
                err.message,
            )
            await lock.release(event.data.hash, lock_id)
            return

        if not asset.ledger_balance_id:
            logger.error(
                "Asset %s has no ledger balance ID for wallet %s",
                asset.asset_id,
                wallet.get_prefixed_id(),
            )
            await lock.release(event.data.hash, lock_id)
            return

        create_transaction_params = create_transaction_params_from_event(
            event_data=event.data,
            wallet=wallet,
            asset_id=asset.id,
            transaction_type=TransactionType.CREDIT,
            countries=config.countries,
        )
        logger.debug("Creating local transaction record for event %s", event.data.id)
        txn, err = await transaction_usecase.create_transaction(
            create_transaction_params
        )
        if err:
            logger.error(
                "Failed to create local transaction for event %s: %s",
                event.data.id,
                err.message,
            )
            await lock.release(event.data.hash, lock_id)
            return
        logger.info("Local transaction record created for event %s", event.data.id)

        # --- Record inflight ledger transaction ---
        try:
            amount = float(event.data.amount)
        except (ValueError, TypeError):
            logger.error(
                "Invalid amount format: %s for event %s",
                event.data.amount,
                event.data.id,
            )
            await lock.release(event.data.hash, lock_id)
            return

        transaction_request = RecordTransactionRequest(
            amount=amount,
            precision=source_asset.precision,
            currency=asset.symbol,
            source=WorldLedger.WORLD_IN,
            destination=asset.ledger_balance_id,
            description=f"Deposit from {event.data.senderAddress}",
            allow_overdraft=True,
            reference=txn.reference,
            inflight=True,
        )
        logger.debug("Recording inflight ledger transaction for event %s", event.data.id)
        ledger_txn, err = await ledger_service.transactions.record_transaction(
            transaction_request
        )
        if err:
            logger.error(
                "Failed to record ledger transaction for event %s: %s",
                event.data.id,
                err.message,
            )
            await lock.release(event.data.hash, lock_id)
            return

        # --- Update DB: set ledger_transaction_id, external_reference, stage=RECEIVED ---
        # Fetch again with deposit relationship
        txn, err = await transaction_usecase.repo.find_one(id=txn.id, load_relationships=["deposit"])

        txn.ledger_transaction_id = ledger_txn.transaction_id
        txn.external_reference = event.data.reference
        if txn.deposit:
            txn.deposit.deposit_stage = DepositStage.RECEIVED
            await transaction_usecase.repo.update(txn.deposit)
        else:
            logger.warning("No DepositDetail found for transaction %s", txn.id)

        _, err = await transaction_usecase.repo.update(txn)
        if err:
            logger.error(
                "Failed to update transaction %s with ledger ID %s: %s",
                txn.get_prefixed_id(),
                ledger_txn.transaction_id,
                err.message,
            )
            await lock.release(event.data.hash, lock_id)
            return

        # --- Cache stage=RECEIVED in Redis so swept task reads it without hitting DB ---
        cache_err = await lock.set_state(event.data.hash, DepositStage.RECEIVED)
        if cache_err:
            logger.warning(
                "Failed to cache RECEIVED stage for hash %s: %s",
                event.data.hash,
                cache_err,
            )

        # --- Release lock (swept task can now acquire and proceed) ---
        err = await lock.release(event.data.hash, lock_id)
        if err:
            logger.error(err)
            return

        logger.info(
            "Deposit success event %s processed. Stage=RECEIVED cached in Redis.",
            event.data.id,
        )


def process_deposit_swept_success_task(event_data: Dict[str, Any]):
    asyncio.run(_process_deposit_swept_success_task_async(event_data))

def process_deposit_success_task(event_data: Dict[str, Any]):
    asyncio.run(_process_deposit_success_task_async(event_data))
