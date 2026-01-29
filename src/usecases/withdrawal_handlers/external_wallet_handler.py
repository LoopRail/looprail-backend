from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.dtos.transaction_dtos import CreateTransactionParams
from src.dtos.wallet_dtos import ExternalWalletTransferData, WithdrawalRequest
from src.infrastructure.logger import get_logger
from src.models import Asset, User
from src.types.blnk import RecordTransactionRequest
from src.types.common_types import WorldLedger
from src.types.error import Error, error
from src.types.types import TransactionType, WithdrawalMethod
from src.usecases.withdrawal_handlers.registry import WithdrawalHandlerRegistry

if TYPE_CHECKING:
    from src.usecases.wallet_usecases import WalletManagerUsecase

logger = get_logger(__name__)


@WithdrawalHandlerRegistry.register_handler(method=WithdrawalMethod.EXTERNAL_WALLET)
async def handle_external_wallet_transfer(
    wallet_manager: WalletManagerUsecase,
    user: User,
    withdrawal_request: WithdrawalRequest,
    external_wallet_transfer_data: ExternalWalletTransferData,
    asset: Asset,
) -> Optional[Error]:
    logger.info(
        "Handling external wallet transfer for user %s to address %s",
        user.id,
        external_wallet_transfer_data.address,
    )
    logger.info(
        "Initiating external wallet transfer for user %s to %s with asset %s amount %s",
        user.id,
        external_wallet_transfer_data.address,
        withdrawal_request.asset_id,
        withdrawal_request.amount,
    )
    # Placeholder for actual transfer logic
    # For example:
    logger.debug("Calling wallet_manager.manager.transfer_asset for user %s", user.id)
    transfer_response, err = await wallet_manager.manager.transfer_asset(
        source_asset_id=asset.asset_id,
        destination_address=external_wallet_transfer_data.address,
        amount=withdrawal_request.amount,
        chain=external_wallet_transfer_data.chain,
    )
    if err:
        logger.error(
            "Failed to initiate external wallet transfer for user %s: %s",
            user.id,
            err.message,
        )
        return error("External wallet transfer failed")
    logger.info(
        "External wallet transfer initiated with transaction ID: %s for user %s",
        transfer_response.transaction_id,
        user.id,
    )

    # Record transaction in local DB and ledger (similar to bank transfer)
    create_transaction_params = CreateTransactionParams(
        wallet_id=asset.wallet_id,
        transaction_type=TransactionType.DEBIT,
        payment_type=TransactionType.DEBIT,
        method=WithdrawalMethod.EXTERNAL_WALLET,
        currency=asset.symbol,
        sender=user.id,
        receiver=external_wallet_transfer_data.address,
        amount=withdrawal_request.amount,
        status="pending",
        transaction_hash=transfer_response.transaction_hash,
        provider_id=transfer_response.transaction_id,
        network=external_wallet_transfer_data.chain.value,
        confirmations=0,
        confirmed=False,
        reference=withdrawal_request.narration,
        note=f"External wallet transfer to {external_wallet_transfer_data.address}",
    )
    logger.debug(
        "Creating local transaction record for user %s with params: %s",
        user.id,
        create_transaction_params.model_dump(),
    )
    _, err = await wallet_manager.service.transaction_usecase.create_transaction(
        create_transaction_params
    )
    if err:
        logger.error(
            "Failed to record local transaction for user %s: %s", user.id, err.message
        )
        return error("Failed to record transaction")
    logger.info(
        "Local transaction record created for user %s with ID: %s",
        user.id,
        create_transaction_params.id,
    )

    transaction_request = RecordTransactionRequest(
        amount=int(withdrawal_request.amount * 100),
        reference=transfer_response.transaction_id,
        source=asset.ledger_balance_id,
        destination=WorldLedger.WORLD_OUT,
        description=withdrawal_request.narration,
    )
    logger.debug(
        "Recording transaction in ledger for user %s with request: %s",
        user.id,
        transaction_request.model_dump(),
    )
    (
        _,
        err,
    ) = await wallet_manager.service.ledger_service.transactions.record_transaction(
        transaction_request
    )
    if err:
        logger.error(
            "Failed to record ledger transaction for user %s: %s", user.id, err.message
        )
        return error("Failed to record ledger transaction")
    logger.info(
        "Ledger transaction recorded for user %s, transaction ID: %s",
        user.id,
        transfer_response.transaction_id,
    )

    return None
