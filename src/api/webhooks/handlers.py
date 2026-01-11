from src.api.webhooks.registry import register
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


@register(event_type=WebhookEventType.DEPOSIT_SUCCESS)
async def handle_deposit_success(
    event: WebhookDepositSuccess,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    asset_repo: AssetRepository,
    transaction_usecase: TransactionUsecase,
):
    logger.info("Handling deposit success event: %s", event.data.id)

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

    asset, err = await asset_repo.get_asset_by_wallet_id_and_asset_type(
        wallet_id=wallet.id, asset_type=event.data.asset.asset_id
    )
    if err:
        logger.error(
            "Asset with type %s not found for wallet %s: %s",
            event.data.asset.asset_id,
            wallet.id,
            err.message,
        )
        return

    if not asset.ledger_balance_id:
        logger.error(
            "Asset %s has no ledger balance ID for wallet %s", asset.asset_id, wallet.id
        )
        return

    create_transaction_params = create_transaction_params_from_event(
        event_data=event.data,
        wallet=wallet,
        transaction_type=TransactionType.CREDIT,
    )
    err = await transaction_usecase.create_transaction(create_transaction_params)
    if err:
        logger.error(
            "Failed to create local transaction record for event %s: %s",
            event.data.id,
            err.message,
        )
        return

    try:
        amount_in_minor_units = int(float(event.data.amount) * 100)
    except (ValueError, TypeError):
        logger.error("Invalid amount format: %s", event.data.amount)
        return

    transaction_request = RecordTransactionRequest(
        amount=amount_in_minor_units,
        reference=event.data.id,
        source=WorldLedger.WORLD,
        destination=asset.ledger_balance_id,
        description=f"Deposit from {event.data.senderAddress}",
    )

    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record deposit transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )


@register(event_type=WebhookEventType.WITHDRAW_SUCCESS)
async def handle_withdraw_success(
    event: WebhookWithdrawSuccess,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    asset_repo: AssetRepository,
    transaction_usecase: TransactionUsecase,
):
    logger.info("Handling withdraw success event: %s", event.data.id)

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

    asset, err = await asset_repo.get_asset_by_wallet_id_and_asset_type(
        wallet_id=wallet.id, asset_type=event.data.asset.asset_id
    )
    if err:
        logger.error(
            "Asset with type %s not found for wallet %s: %s",
            event.data.asset.asset_id,
            wallet.id,
            err.message,
        )
        return

    if not asset.ledger_balance_id:
        logger.error(
            "Asset %s has no ledger balance ID for wallet %s", asset.asset_id, wallet.id
        )
        return

    create_transaction_params = create_transaction_params_from_event(
        event_data=event.data,
        wallet=wallet,
        transaction_type=TransactionType.DEBIT,
    )
    err = await transaction_usecase.create_transaction(create_transaction_params)
    if err:
        logger.error(
            "Failed to create local transaction record for event %s: %s",
            event.data.id,
            err.message,
        )
        return

    try:
        amount_in_minor_units = int(float(event.data.amount) * 100)
    except (ValueError, TypeError):
        logger.error("Invalid amount format: %s", event.data.amount)
        return

    transaction_request = RecordTransactionRequest(
        amount=amount_in_minor_units,
        reference=event.data.id,
        source=asset.ledger_balance_id,
        destination=WorldLedger.WORLD,
        description=f"Withdrawal to {event.data.recipientAddress}",
    )

    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record withdrawal transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )
        return
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
    err = await transaction_usecase.update_status_from_event(event.data)
    if err:
        logger.error(
            "Failed to update local transaction status for event %s: %s",
            event.data.id,
            err.message,
        )
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

    asset, err = await asset_repo.get_asset_by_wallet_id_and_asset_type(
        wallet_id=wallet.id, asset_type=event.data.asset.asset_id
    )
    if err:
        logger.error(
            "Asset with type %s not found for wallet %s: %s",
            event.data.asset.asset_id,
            wallet.id,
            err.message,
        )
        return

    if not asset.ledger_balance_id:
        logger.error(
            "Asset %s has no ledger balance ID for wallet %s", asset.asset_id, wallet.id
        )
        return

    transaction_request = RecordTransactionRequest(
        amount=0,
        reference=event.data.id,
        source=asset.ledger_balance_id,
        destination=WorldLedger.WORLD,
        description=f"Failed withdrawal to {event.data.recipientAddress}. Reason: {event.data.reason}",
    )

    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record failed withdrawal transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )
        return
    return


@register(event_type=WebhookEventType.WITHDRAW_CANCELLED)
async def handle_withdraw_cancelled(
    event: WebhookWithdrawCancelled,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    asset_repo: AssetRepository,
    transaction_usecase: TransactionUsecase,
):
    logger.info("Handling withdraw cancelled event: %s", event.data.id)
    err = await transaction_usecase.update_status_from_event(event.data)
    if err:
        logger.error(
            "Failed to update local transaction status for event %s: %s",
            event.data.id,
            err.message,
        )
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

    asset, err = await asset_repo.get_asset_by_wallet_id_and_asset_type(
        wallet_id=wallet.id, asset_type=event.data.asset.asset_id
    )
    if err:
        logger.error(
            "Asset with type %s not found for wallet %s: %s",
            event.data.asset.asset_id,
            wallet.id,
            err.message,
        )
        return

    if not asset.ledger_balance_id:
        logger.error(
            "Asset %s has no ledger balance ID for wallet %s", asset.asset_id, wallet.id
        )
        return

    transaction_request = RecordTransactionRequest(
        amount=0,
        reference=event.data.id,
        source=asset.ledger_balance_id,
        destination=WorldLedger.WORLD,
        description=f"Cancelled withdrawal to {event.data.recipientAddress}. Reason: {event.data.reason}",
    )

    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record cancelled withdrawal transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )
