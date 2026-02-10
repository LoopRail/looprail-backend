from typing import TYPE_CHECKING, Optional, Tuple

from src.dtos.transaction_dtos import (BankTransferParams,
                                       CreateTransactionParams)
from src.dtos.wallet_dtos import BankTransferData, WithdrawalRequest
from src.infrastructure.logger import get_logger
from src.models import Transaction, User
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
    create_transaction_params: CreateTransactionParams,
    **kwargs,
) -> Tuple[Optional[Transaction], Optional[Error]]:
    logger.info(
        "Handling bank transfer for user %s to account %s",
        user.id,
        transfer_data.account_number,
    )

    # Populate the existing CreateTransactionParams with method-specific details
    bank_transfer_specific_params = BankTransferParams(
        **create_transaction_params.model_dump(),  # Start with common params
        external_reference=None,  # Not available at this stage
        bank_code=transfer_data.bank_code,
        bank_name=transfer_data.bank_name,
        account_number=transfer_data.account_number,
        account_name=transfer_data.account_name,
        provider=None,
        session_id=None,
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

    return transaction, None
