from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from src.dtos.transaction_dtos import CreateTransactionParams, CryptoTransactionParams
from src.dtos.wallet_dtos import ExternalWalletTransferData, WithdrawalRequest
from src.infrastructure.logger import get_logger
from src.models import Asset, Transaction, User
from src.types.blnk import RecordTransactionRequest
from src.types.common_types import WorldLedger
from src.types.error import Error, error
from src.types.types import TransactionStatus, WithdrawalMethod
from src.usecases.withdrawal_handlers.registry import WithdrawalHandlerRegistry

if TYPE_CHECKING:
    from src.usecases.wallet_usecases import WalletManagerUsecase

logger = get_logger(__name__)


@WithdrawalHandlerRegistry.register_handler(method=WithdrawalMethod.EXTERNAL_WALLET)
async def handle_external_wallet_transfer(
    wallet_manager: WalletManagerUsecase,
    user: User,
    withdrawal_request: WithdrawalRequest,
    transfer_data: ExternalWalletTransferData,
    asset: Asset,
    create_transaction_params: CreateTransactionParams,
    **kwargs
) -> Tuple[Optional[Transaction], Optional[Error]]:
    logger.info(
        "Handling external wallet transfer for user %s to address %s",
        user.id,
        transfer_data.address,
    )
    logger.info(
        "Initiating external wallet transfer for user %s to %s with asset %s amount %s",
        user.id,
        transfer_data.address,
        withdrawal_request.asset_id,
        withdrawal_request.amount,
    )
    # Placeholder for actual transfer logic
    # For example:
    logger.debug("Calling wallet_manager.manager.transfer_asset for user %s", user.id)
    transfer_response, err = await wallet_manager.manager.transfer_asset(
        source_asset_id=asset.asset_id,
        destination_address=transfer_data.address,
        amount=withdrawal_request.amount,
        chain=transfer_data.chain,
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
    # Populate the existing CreateTransactionParams with method-specific details
    crypto_specific_params = CryptoTransactionParams(
        **create_transaction_params.model_dump(),  # Start with common params
        status=TransactionStatus.PENDING,
        transaction_hash=transfer_response.transaction_hash,
        provider_id=transfer_response.transaction_id,
        network=transfer_data.chain.value,
        chain_id=transfer_data.chain.value, # Assuming chain.value is suitable for chain_id
        confirmations=0,
        confirmed=False,
    )

    logger.debug(
        "Creating local transaction record for user %s with params: %s",
        user.id,
        crypto_specific_params.model_dump(),
    )
    transaction, err = await wallet_manager.service.transaction_usecase.create_transaction(
        crypto_specific_params
    )
    if err:
        logger.error(
            "Failed to record local transaction for user %s: %s", user.id, err.message
        )
        return None, error("Failed to record transaction")
    logger.info(
        "Local transaction record created for user %s with ID: %s",
        user.id,
        transaction.id,
    )

    transaction_request = RecordTransactionRequest(
        amount=int(withdrawal_request.amount * 100),
        reference=transaction.get_prefixed_id(), 
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
        # Attempt to mark the local transaction as failed if ledger recording fails
        await wallet_manager.service.transaction_usecase.update_transaction_status(
            transaction_id=transaction.id,
            new_status="FAILED",
            message="Ledger record failed",
        )
        return None, error("Failed to record ledger transaction")
    logger.info(
        "Ledger transaction recorded for user %s, transaction ID: %s",
        user.id,
        transaction.id,
    )

    return transaction, None
