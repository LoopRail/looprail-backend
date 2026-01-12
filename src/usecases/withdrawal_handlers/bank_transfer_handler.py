from typing import Optional

from src.dtos.transaction_dtos import CreateTransactionParams
from src.dtos.wallet_dtos import BankTransferData, WithdrawalRequest
from src.infrastructure.logger import get_logger
from src.models import Asset, User
from src.types.blnk import RecordTransactionRequest
from src.types.error import Error, error
from src.types.types import TransactionType, WithdrawalMethod, WorldLedger
from src.usecases.wallet_usecases import \
    WalletManagerUsecase  
from src.usecases.withdrawal_handlers.registry import \
    register_withdrawal_handler

logger = get_logger(__name__)


@register_withdrawal_handler(method=WithdrawalMethod.BANK_TRANSFER)
async def handle_bank_transfer(
    wallet_manager: WalletManagerUsecase,
    user: User,
    withdrawal_request: WithdrawalRequest,
    bank_transfer_data: BankTransferData,
    asset: Asset,
) -> Optional[Error]:
    (
        transfer_code,
        err,
    ) = await wallet_manager.service.paystack_service.initiate_transfer(
        amount=withdrawal_request.amount,
        recipient_bank_code=bank_transfer_data.bank_code,
        recipient_account_number=bank_transfer_data.account_number,
        recipient_name=bank_transfer_data.account_name,
        narration=withdrawal_request.narration,
    )
    if err:
        logger.error(
            "Paystack transfer initiation failed for user %s: %s",
            user.id,
            err.message,
        )
        return error("Bank transfer failed")

    # Record transaction in local DB
    create_transaction_params = CreateTransactionParams(
        wallet_id=asset.wallet_id,
        transaction_type=TransactionType.DEBIT,
        method=WithdrawalMethod.BANK_TRANSFER,
        currency=asset.symbol,
        sender=user.id,  # This could be the user's wallet address or similar
        receiver=bank_transfer_data.account_number,
        amount=withdrawal_request.amount,
        status="pending",  # Initial status
        transaction_hash=transfer_code,  # Paystack transfer code as hash
        provider_id=transfer_code,  # Paystack transfer code as provider ID
        network="N/A",  # Not applicable for bank transfer
        confirmations=0,  # Not applicable
        confirmed=False,  # Not confirmed initially
        reference=withdrawal_request.narration,
        note=f"Bank transfer to {bank_transfer_data.account_name}",
    )
    _, err = await wallet_manager.service.transaction_usecase.create_transaction(
        create_transaction_params
    )
    if err:
        logger.error(
            "Failed to record local transaction for user %s: %s", user.id, err.message
        )
        return error("Failed to record transaction")

    # Record transaction in ledger
    transaction_request = RecordTransactionRequest(
        amount=int(withdrawal_request.amount * 100),  # Convert to minor units
        reference=transfer_code,
        source=asset.ledger_balance_id,
        destination=WorldLedger.WORLD,  # To external world
        description=withdrawal_request.narration,
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

    return None
