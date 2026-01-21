from src.api.webhooks.registry import register
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import AssetRepository, WalletRepository
from src.infrastructure.services import LedgerService
from src.types import TransactionType, WorldLedger
from src.types.blnk import RecordTransactionRequest
from src.types.blockrader import (
    WebhookDepositSuccess,
    WebhookEventType,
    WebhookWithdrawCancelled,
    WebhookWithdrawFailed,
    WebhookWithdrawSuccess,
)
from src.usecases import TransactionUsecase
from src.utils import create_transaction_params_from_event

logger = get_logger(__name__)


# TODO  catch alredy proccessed transactions
@register(event_type=WebhookEventType.DEPOSIT_SUCCESS)
async def handle_deposit_success(
    event: WebhookDepositSuccess,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    asset_repo: AssetRepository,
    transaction_usecase: TransactionUsecase,
    config: Config,
):
    logger.info("Handling deposit success event: %s", event.data.id)
    logger.debug(
        "Attempting to get wallet for recipient address: %s",
        event.data.recipientAddress,
    )
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
        event.data.asset.asset_id,
        wallet.get_prefixed_id(),
    )
    asset, err = await asset_repo.get_asset_by_wallet_id_and_asset_id(
        wallet_id=wallet.id, asset_id=event.data.asset.asset_id
    )
    if err:
        logger.error(
            "Asset with ID %s not found for wallet %s: %s",
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
    )  # TODO add more metadata here
    logger.debug("Recording transaction on ledger for event %s", event.data.id)
    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record deposit transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )
        return
    logger.info("Deposit transaction successfully recorded on ledger for event %s", event.data.id)


@register(event_type=WebhookEventType.WITHDRAW_SUCCESS)
async def handle_withdraw_success(
    event: WebhookWithdrawSuccess,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    asset_repo: AssetRepository,
    transaction_usecase: TransactionUsecase,
    config: Config,
):
    logger.info("Handling withdraw success event: %s", event.data.id)
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
    asset, err = await asset_repo.get_asset_by_wallet_id_and_asset_id(
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
    logger.info("Withdrawal transaction successfully recorded on ledger for event %s", event.data.id)
    return


@register(event_type=WebhookEventType.WITHDRAW_FAILED)
async def handle_withdraw_failed(
    event: WebhookWithdrawFailed,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    asset_repo: AssetRepository,
    transaction_usecase: TransactionUsecase,
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
    asset, err = await asset_repo.get_asset_by_wallet_id_and_asset_id(
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
        "Failed withdrawal transaction successfully recorded on ledger for event %s", event.data.id
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
    asset, err = await asset_repo.get_asset_by_wallet_id_and_asset_id(
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
