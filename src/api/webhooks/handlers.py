from src.types import PaymentMethod, TransactionType
from src.dtos import CreateTransactionParams

from src.api.webhooks.registry import register
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import WalletRepository
from src.infrastructure.services.ledger import LedgerService
from src.types.blnk.dtos import RecordTransactionRequest
from src.types.blockrader.webhook_dtos import (
    WebhookDepositSuccess,
    WebhookEventType,
    WebhookWithdrawCancelled,
    WebhookWithdrawFailed,
    WebhookWithdrawSuccess,
)
from src.usecases.transaction_usecases import TransactionUsecase

logger = get_logger(__name__)

TREASURY_BALANCE_ID = "@world"  # TODO  we need to change this


@register(event_type=WebhookEventType.DEPOSIT_SUCCESS)
async def handle_deposit_success(
    event: WebhookDepositSuccess,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    transaction_usecase: TransactionUsecase,
):
    logger.info("Handling deposit success event: %s", event.data.id)

    wallet, err = await wallet_repo.get_wallet_by_address(
        address=event.data.recipientAddress
    )
    # TODO add checks here to make sure the user is still active or somthing
    if err:
        logger.error(
            "Wallet not found for address %s: %s",
            event.data.recipientAddress,
            err.message,
        )
        return

    await transaction_usecase.create_transaction(create_transaction_params)

    if not wallet.ledger_balance_id:
        logger.error("Wallet %s has no ledger balance ID", wallet.id)
        return

    try:
        # Assuming amount is in major units, converting to minor units (cents)
        amount_in_minor_units = int(float(event.data.amount) * 100)
    except (ValueError, TypeError):
        logger.error("Invalid amount format: %s", event.data.amount)
        return

    transaction_request = RecordTransactionRequest(
        amount=amount_in_minor_units,
        reference=event.data.id,
        source=TREASURY_BALANCE_ID,
        destination=wallet.ledger_balance_id,
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

    create_transaction_params = CreateTransactionParams(
        wallet_id=wallet.id,
        transaction_type=TransactionType.DEBIT,
        method=PaymentMethod.WALLET_TRANSFER,  # Assuming, as PaymentMethod doesn't have crypto
        currency=event.data.currency,
        sender=event.data.senderAddress,
        receiver=event.data.recipientAddress,
        amount=Decimal(event.data.amount),
        status=event.data.status.value,
        transaction_hash=event.data.hash,
        provider_id=event.data.id,
        network=event.data.network,
        confirmations=event.data.confirmations,
        confirmed=event.data.confirmed,
        reference=event.data.reference,
        block_hash=event.data.blockHash,
        block_number=event.data.blockNumber,
        gas_price=event.data.gasPrice,
        gas_fee=event.data.gasFee,
        gas_used=event.data.gasUsed,
        note=event.data.note,
        chain_id=event.data.chainId,
        reason=event.data.reason,
        fee=Decimal(event.data.fee) if event.data.fee else None,
    )
    await transaction_usecase.create_transaction(create_transaction_params)

    if not wallet.ledger_balance_id:
        logger.error("Wallet %s has no ledger balance ID", wallet.id)
        return

    try:
        amount_in_minor_units = int(float(event.data.amount) * 100)
    except (ValueError, TypeError):
        logger.error("Invalid amount format: %s", event.data.amount)
        return

    transaction_request = RecordTransactionRequest(
        amount=amount_in_minor_units,
        reference=event.data.id,
        source=wallet.ledger_balance_id,
        destination=TREASURY_BALANCE_ID,
        description=f"Withdrawal to {event.data.recipientAddress}",
    )

    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record withdrawal transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )


@register(event_type=WebhookEventType.WITHDRAW_FAILED)
async def handle_withdraw_failed(
    event: WebhookWithdrawFailed,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    transaction_usecase: TransactionUsecase,
):
    logger.info("Handling withdraw failed event: %s", event.data.id)
    await transaction_usecase.update_status_from_event(event.data)

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

    if not wallet.ledger_balance_id:
        logger.error("Wallet %s has no ledger balance ID", wallet.id)
        return

    transaction_request = RecordTransactionRequest(
        amount=0,
        reference=event.data.id,
        source=wallet.ledger_balance_id,
        destination=TREASURY_BALANCE_ID,
        description=f"Failed withdrawal to {event.data.recipientAddress}. Reason: {event.data.reason}",
    )

    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record failed withdrawal transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )


@register(event_type=WebhookEventType.WITHDRAW_CANCELLED)
async def handle_withdraw_cancelled(
    event: WebhookWithdrawCancelled,
    ledger_service: LedgerService,
    wallet_repo: WalletRepository,
    transaction_usecase: TransactionUsecase,
):
    logger.info("Handling withdraw cancelled event: %s", event.data.id)
    await transaction_usecase.update_status_from_event(event.data)

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

    if not wallet.ledger_balance_id:
        logger.error("Wallet %s has no ledger balance ID", wallet.id)
        return

    transaction_request = RecordTransactionRequest(
        amount=0,
        reference=event.data.id,
        source=wallet.ledger_balance_id,
        destination=TREASURY_BALANCE_ID,
        description=f"Cancelled withdrawal to {event.data.recipientAddress}. Reason: {event.data.reason}",
    )

    _, err = await ledger_service.transactions.record_transaction(transaction_request)
    if err:
        logger.error(
            "Failed to record cancelled withdrawal transaction on ledger for event %s: %s",
            event.data.id,
            err.message,
        )
