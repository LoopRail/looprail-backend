from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from src.dtos.transaction_dtos import CreateTransactionParams, CryptoTransactionParams
from src.dtos.wallet_dtos import ExternalWalletTransferData, WithdrawalRequest
from src.infrastructure.logger import get_logger
from src.models import Transaction, User
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
    create_transaction_params: CreateTransactionParams,
    **kwargs,
) -> Tuple[Optional[Transaction], Optional[Error]]:
    logger.info(
        "Handling external wallet transfer for user %s to address %s",
        user.id,
        transfer_data.address,
    )
    logger.info(
        "Preparing external wallet transfer for user %s to %s with asset %s amount %s",
        user.id,
        transfer_data.address,
        withdrawal_request.asset_id,
        withdrawal_request.amount,
    )
    crypto_specific_params = CryptoTransactionParams(
        **create_transaction_params.model_dump(),
        status=TransactionStatus.PENDING,
        provider_id=None,
    )

    logger.debug(
        "Creating local transaction record for user %s with params: %s",
        user.id,
        crypto_specific_params.model_dump(),
    )
    (
        transaction,
        err,
    ) = await wallet_manager.service.transaction_usecase.create_transaction(
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

    return transaction, None
