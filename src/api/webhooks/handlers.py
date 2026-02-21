from src.api.webhooks.registry import register
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import (
    AssetRepository,
    TransactionRepository,
    WalletRepository,
)
from src.infrastructure.services import LedgerService, LockService
from src.types import NotFoundError, TransactionType, WorldLedger
from src.types.blnk import RecordTransactionRequest
from src.types.blnk.dtos import UpdateInflightTransactionRequest
from src.types.blockrader import (
    WebhookDepositSuccess,
    WebhookDepositSweptSuccess,
    WebhookEventType,
    WebhookWithdrawCancelled,
    WebhookWithdrawFailed,
    WebhookWithdrawSuccess,
)
from src.usecases import TransactionUsecase
from src.utils import create_transaction_params_from_event

logger = get_logger(__name__)


@register(event_type=WebhookEventType.DEPOSIT_SWEPT_SUCCESS)
async def handle_deposit_swept_success(
    event: WebhookDepositSweptSuccess,
    ledger_service: LedgerService,
    transaction_repo: TransactionRepository,
    config: Config,
    lock_service: LockService,
    **kwargs,
):
    logger.info("Handling deposit swept success event: %s", event.data.id)

    logger.debug(
        "Attempting to get source wallet for recipient address: %s",
        event.data.recipientAddress,
    )
    lock = lock_service.get("deposits")
    lock_id, err = await lock.acquire(event.data.hash)
    if err:
        logger.error(err)
        return
    source_wallet, err = config.block_rader.wallets.get_wallet(
        wallet_id=event.data.wallet.wallet_id
    )
    if err:
        logger.error(
            "Source wallet not found for address %s: %s",
            event.data.recipientAddress,
            err.message,
        )
        return
    logger.debug("Source wallet found: %s", source_wallet.wallet_name)

    source_asset, err = source_wallet.get(asset_id=event.data.asset.asset_id)

    if err:
        logger.error(
            "Swept asset with ID %s not found in source wallet %s",
            event.data.asset.asset_id,
            source_wallet.wallet_name,
        )
        return
    logger.debug("Processing swept transaction for asset %s", source_asset.name)

    txn, err = await transaction_repo.find_one(external_reference=event.data.reference)
    if err:
        logger.error(
            "Error getting transaction with reference %s Error: %s",
            event.data.reference,
            err,
        )
    try:
        amount_in_minor_units = int(float(event.data.amount) * 100)
        logger.debug(
            "Converted amount %s to minor units: %s",
            event.data.amount,
            amount_in_minor_units,
        )
    except (ValueError, TypeError):
        logger.error(
            "Invalid amount format: %s for event %s", event.data.amount, event.data.id
        )
        return

    transaction_request = UpdateInflightTransactionRequest(
        status="commit", amount=amount_in_minor_units
    )
    logger.debug("Recording transaction on ledger for event %s", event.data.id)
    _, err = await ledger_service.transactions.update_inflight_transaction(
        txn.ledger_transaction_id, transaction_request
    )
    if err:
        logger.error(
            "Failed to record deposit swept transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )
        return
    err = await lock.release(event.data.hash, lock_id)
    if err:
        logger.error(err)
        return
    logger.info(
        "Deposit swept transaction successfully recorded on ledger for event %s",
        event.data.id,
    )


@register(event_type=WebhookEventType.DEPOSIT_SUCCESS)
async def handle_deposit_success(
    event: WebhookDepositSuccess,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    asset_repo: AssetRepository,
    lock_service: LockService,
    transaction_usecase: TransactionUsecase,
    config: Config,
    **kwargs,
):
    logger.info("Handling deposit swept success event: %s", event.data.id)

    logger.debug(
        "Attempting to get source wallet for recipient address: %s",
        event.data.recipientAddress,
    )
    lock = lock_service.get("deposits")
    lock_id, err = await lock.acquire(event.data.hash)
    if err:
        logger.error(err)
        return
    txn, err = await transaction_usecase.repo.find_one(transaction_hash=event.data.hash)
    if err and err != NotFoundError:
        logger.error(err)
        return
    if txn:
        logger.info(
            "Transaction hash %s found with ID %s status %s",
            event.data.hash,
            txn.id,
            txn.status,
        )
        return

    source_wallet, err = config.block_rader.wallets.get_wallet(
        wallet_id=event.data.wallet.wallet_id
    )
    if err:
        logger.error(
            "Source wallet not found for address %s: %s",
            event.data.recipientAddress,
            err.message,
        )
        return
    logger.debug("Source wallet found: %s", source_wallet.wallet_name)

    source_asset, err = source_wallet.get(asset_id=event.data.asset.asset_id)

    if err:
        logger.error(
            "Swept asset with ID %s not found in source wallet %s",
            event.data.asset.asset_id,
            source_wallet.wallet_name,
        )
        return
    logger.debug("Processing swept transaction for asset %s", source_asset.name)

    wallet, err = await wallet_repo.get_wallet_by_address(
        address=event.data.recipientAddress
    )
    if err:
        logger.error(
            "Wallet not found for address %s: %s",
            event.data.recipientAddress,
            err.message,
        )
        return
    logger.debug("Wallet found: %s", wallet.get_prefixed_id())

    logger.debug(
        "Attempting to get asset %s for wallet %s",
        source_asset.asset_id,
        wallet.get_prefixed_id(),
    )
    asset, err = await asset_repo.find_one(
        wallet_id=wallet.id, asset_id=source_asset.asset_id
    )
    if err:
        logger.error(
            "Asset with ID %s not found for wallet %s: %s",
            source_asset.asset_id,
            wallet.get_prefixed_id(),
            err.message,
        )
        return
    logger.debug("Asset found: %s", asset.get_prefixed_id())

    if not asset.ledger_balance_id:
        logger.error(
            "Asset %s has no ledger balance ID for wallet %s",
            asset.asset_id,
            wallet.get_prefixed_id(),
        )
        return
    logger.debug("Asset ledger balance ID: %s", asset.ledger_balance_id)

    create_transaction_params = create_transaction_params_from_event(
        event_data=event.data,
        wallet=wallet,
        asset_id=asset.id,
        transaction_type=TransactionType.CREDIT,
        countries=config.countries,
    )
    logger.debug("Creating local transaction record for event %s", event.data.id)
    txn, err = await transaction_usecase.create_transaction(create_transaction_params)
    if err:
        logger.error(
            "Failed to create local transaction record for event %s: %s",
            event.data.id,
            err.message,
        )
        return
    logger.info("Local transaction record created for event %s", event.data.id)

    try:
        amount_in_minor_units = int(float(event.data.amount) * 100)
        logger.debug(
            "Converted amount %s to minor units: %s",
            event.data.amount,
            amount_in_minor_units,
        )
    except (ValueError, TypeError):
        logger.error(
            "Invalid amount format: %s for event %s", event.data.amount, event.data.id
        )
        return

    transaction_request = RecordTransactionRequest(
        amount=amount_in_minor_units,
        currency=asset.symbol,
        source=WorldLedger.WORLD_IN,
        destination=asset.ledger_balance_id,
        description=f"Deposit from {event.data.senderAddress}",
        allow_overdraft=True,
        reference=txn.reference,
        inflight=True,
    )
    logger.debug("Recording transaction on ledger for event %s", event.data.id)
    ledger_txn, err = await ledger_service.transactions.record_transaction(
        transaction_request
    )
    if err:
        logger.error(
            "Failed to record deposit transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )
        return
    txn.ledger_transaction_id = ledger_txn.transaction_id
    txn.external_reference = event.data.reference
    _, err = await transaction_usecase.repo.update(txn)
    if err:
        logger.error(
            "Failed to update transaction %s on ledger with ledger trasnaction ID %s Error: %s",
            txn.get_prefixed_id(),
            ledger_txn.transaction_id,
            err.message,
        )
        return
    err = await lock.release(event.data.hash, lock_id)
    if err:
        logger.error(err)
        return
    logger.info(
        "Deposit transaction successfully recorded on ledger for event %s",
        event.data.id,
    )


@register(event_type=WebhookEventType.WITHDRAW_SUCCESS)
async def handle_withdraw_success(
    event: WebhookWithdrawSuccess,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    asset_repo: AssetRepository,
    transaction_usecase: TransactionUsecase,
    lock_service: LockService,
    config: Config,
    **kwargs,
):
    logger.info("Handling withdraw success event: %s", event.data.id)
    logger.debug(
        "Attempting to get wallet for sender address: %s", event.data.senderAddress
    )
    lock = lock_service.get("withdrawals")
    lock_id, err = await lock.acquire(event.data.hash)
    if err:
        logger.error(err)
        return
    txn, err = await transaction_usecase.repo.find_one(transaction_hash=event.data.hash)
    if err and err != NotFoundError:
        logger.debug(
            "Transaction hash %s found ID %s status %s",
            txn.transaction_hash,
            txn.id,
            txn.status,
        )
        logger.error(err)
        return
    wallet, err = await wallet_repo.get_wallet_by_address(
        address=event.data.senderAddress
    )
    if err:
        logger.error(
            "Wallet not found for address %s: %s",
            event.data.senderAddress,
            err.message,
        )
        return
    logger.debug("Wallet found: %s", wallet.get_prefixed_id())

    logger.debug(
        "Attempting to get asset %s for wallet %s",
        event.data.asset.asset_id,
        wallet.get_prefixed_id(),
    )
    asset, err = await asset_repo.find_one(
        wallet_id=wallet.id, asset_id=event.data.asset.asset_id
    )
    if err:
        logger.error(
            "Asset with type %s not found for wallet %s: %s",
            event.data.asset.asset_id,
            wallet.get_prefixed_id(),
            err.message,
        )
        return
    logger.debug("Asset found: %s", asset.get_prefixed_id())

    if not asset.ledger_balance_id:
        logger.error(
            "Asset %s has no ledger balance ID for wallet %s",
            asset.asset_id,
            wallet.get_prefixed_id(),
        )
        return
    logger.debug("Asset ledger balance ID: %s", asset.ledger_balance_id)

    create_transaction_params = create_transaction_params_from_event(
        event_data=event.data,
        wallet=wallet,
        asset_id=event.data.asset.asset_id,
        transaction_type=TransactionType.DEBIT,
        countries=config.countries,
    )
    logger.debug("Creating local transaction record for event %s", event.data.id)
    err = await transaction_usecase.create_transaction(create_transaction_params)
    if err:
        logger.error(
            "Failed to create local transaction record for event %s: %s",
            event.data.id,
            err.message,
        )
        return
    logger.info("Local transaction record created for event %s", event.data.id)

    try:
        amount_in_minor_units = int(float(event.data.amount) * 100)
        logger.debug(
            "Converted amount %s to minor units: %s",
            event.data.amount,
            amount_in_minor_units,
        )
    except (ValueError, TypeError):
        logger.error(
            "Invalid amount format: %s for event %s", event.data.amount, event.data.id
        )
        return

    transaction_request = RecordTransactionRequest(
        amount=amount_in_minor_units,
        reference=event.data.id,
        currency=event.data.currency,
        source=asset.ledger_balance_id,
        destination=WorldLedger.WORLD_OUT,
        description=f"Withdrawal to {event.data.recipientAddress}",
    )
    logger.debug("Recording transaction on ledger for event %s", event.data.id)
    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record withdrawal transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )
        return

    err = await lock.release(event.data.hash, lock_id)
    if err:
        logger.error(err)
        return
    logger.info(
        "Withdrawal transaction successfully recorded on ledger for event %s",
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

    logger.debug(
        "Attempting to get wallet for sender address: %s", event.data.senderAddress
    )
    wallet, err = await wallet_repo.get_wallet_by_address(
        address=event.data.senderAddress
    )
    if err:
        logger.error(
            "Wallet not found for address %s: %s",
            event.data.senderAddress,
            err.message,
        )
        return
    logger.debug("Wallet found: %s", wallet.get_prefixed_id())

    logger.debug(
        "Attempting to get asset %s for wallet %s",
        event.data.asset.asset_id,
        wallet.get_prefixed_id(),
    )
    asset, err = await asset_repo.find_one(
        wallet_id=wallet.id, asset_id=event.data.asset.asset_id
    )
    if err:
        logger.error(
            "Asset with type %s not found for wallet %s: %s",
            event.data.asset.asset_id,
            wallet.get_prefixed_id(),
            err.message,
        )
        return
    logger.debug("Asset found: %s", asset.get_prefixed_id())

    if not asset.ledger_balance_id:
        logger.error(
            "Asset %s has no ledger balance ID for wallet %s",
            asset.asset_id,
            wallet.get_prefixed_id(),
        )
        return
    logger.debug("Asset ledger balance ID: %s", asset.ledger_balance_id)

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
    config: Config,
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

    logger.debug(
        "Attempting to get wallet for sender address: %s", event.data.senderAddress
    )
    wallet, err = await wallet_repo.get_wallet_by_address(
        address=event.data.senderAddress
    )
    if err:
        logger.error(
            "Wallet not found for address %s: %s",
            event.data.senderAddress,
            err.message,
        )
        return
    logger.debug("Wallet found: %s", wallet.get_prefixed_id())

    logger.debug(
        "Attempting to get asset %s for wallet %s",
        event.data.asset.asset_id,
        wallet.get_prefixed_id(),
    )
    asset, err = await asset_repo.find_one(
        wallet_id=wallet.id, asset_id=event.data.asset.asset_id
    )
    if err:
        logger.error(
            "Asset with type %s not found for wallet %s: %s",
            event.data.asset.asset_id,
            wallet.get_prefixed_id(),
            err.message,
        )
        return
    logger.debug("Asset found: %s", asset.get_prefixed_id())

    if not asset.ledger_balance_id:
        logger.error(
            "Asset %s has no ledger balance ID for wallet %s",
            asset.asset_id,
            wallet.get_prefixed_id(),
        )
        return
    logger.debug("Asset ledger balance ID: %s", asset.ledger_balance_id)

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
