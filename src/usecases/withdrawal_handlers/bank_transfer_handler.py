from typing import TYPE_CHECKING, Optional, Tuple

from src.dtos.transaction_dtos import (BankTransferParams,
                                       CreateTransactionParams)
from src.dtos.wallet_dtos import BankTransferData, WithdrawalRequest
from src.infrastructure.logger import get_logger
from src.models import Asset, Transaction, User
from src.types.blnk import RecordTransactionRequest
from src.types.common_types import WorldLedger
from src.types.error import Error, error
from src.types.types import WithdrawalMethod
from src.usecases.withdrawal_handlers.registry import WithdrawalHandlerRegistry

if TYPE_CHECKING:
    from src.usecases.wallet_usecases import WalletManagerUsecase


logger = get_logger(__name__)


@WithdrawalHandlerRegistry.register_handler(method=WithdrawalMethod.BANK_TRANSFER)
async def handle_bank_transfer(
    wallet_manager: "WalletManagerUsecase",
    user: User,
    withdrawal_request: WithdrawalRequest,
    transfer_data: BankTransferData,
    asset: Asset,
    create_transaction_params: CreateTransactionParams,
    **kwargs,
) -> Tuple[Optional[Transaction], Optional[Error]]:
    logger.info(
        "Handling bank transfer for user %s to account %s",
        user.id,
        transfer_data.account_number,
    )
    logger.debug(
        "Initiating Paystack transfer for user %s, amount %s",
        user.id,
        withdrawal_request.amount,
    )
    (
        transfer_code,
        err,
    ) = await wallet_manager.service.paystack_service.initiate_transfer(
        amount=withdrawal_request.amount,
        recipient_bank_code=transfer_data.bank_code,
        recipient_account_number=transfer_data.account_number,
        recipient_name=transfer_data.account_name,
        narration=withdrawal_request.narration,
    )
    if err:
        logger.error(
            "Paystack transfer initiation failed for user %s: %s",
            user.id,
            err.message,
        )
        return None, error("Bank transfer failed")
    logger.info(
        "Paystack transfer initiated successfully with transfer code: %s for user %s",
        transfer_code,
        user.id,
    )

    # Populate the existing CreateTransactionParams with method-specific details
    bank_transfer_specific_params = BankTransferParams(
        **create_transaction_params.model_dump(),  # Start with common params
        external_reference=transfer_code,
        bank_code=transfer_data.bank_code,
        bank_name=transfer_data.bank_name,  # Assuming bank name is available or can be fetched
        account_number=transfer_data.account_number,
        account_name=transfer_data.account_name,
        provider="Paystack",  # Assuming Paystack is the provider for bank transfers
        session_id=None,  # Session ID might come from a higher level, setting to None for now
    )

    logger.debug(
        "Creating local transaction record for user %s with params: %s",
        user.id,
        bank_transfer_specific_params.model_dump(),
    )
    (
        transaction,
        err,
    ) = await wallet_manager.service.transaction_usecase.create_transaction(
        bank_transfer_specific_params
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

    # Record transaction in ledger
    transaction_request = RecordTransactionRequest(
        amount=int(withdrawal_request.amount * 100),  # Convert to minor units
        reference=transaction.get_prefixed_id(),  # Use internal transaction ID as reference for ledger
        source=asset.ledger_balance_id,
        destination=WorldLedger.WORLD_OUT,  # To external world
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
