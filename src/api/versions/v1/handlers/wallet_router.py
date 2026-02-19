from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    get_auth_lock_service,
    get_config,
    get_current_user,
    get_user_usecases,
    get_wallet_manager_usecase,
)
from src.api.dependencies.extra_deps import get_rq_manager
from src.api.rate_limiters.rate_limiter import custom_rate_limiter
from src.dtos.wallet_dtos import WithdrawalRequest
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.redis import RQManager
from src.infrastructure.services import AuthLockService
from src.infrastructure.tasks.withdrawal_tasks import process_withdrawal_task
from src.models import User
from src.usecases import UserUseCase, WalletManagerUsecase

logger = get_logger(__name__)

router = APIRouter(prefix="/wallets", tags=["Wallets"])

withdraw_auth_lock = get_auth_lock_service("withdrawals")


@router.post("/withdraw", status_code=status.HTTP_200_OK)
@custom_rate_limiter(
    limit_type="withdrawal", identifier_arg="user", identifier_field="email"
)
async def withdraw(
    request: Request,
    withdrawal_request: WithdrawalRequest,
    user: User = Depends(get_current_user),
    wallet_manager: WalletManagerUsecase = Depends(get_wallet_manager_usecase),
    config: Config = Depends(get_config),
    rq_manager: RQManager = Depends(get_rq_manager),
    user_usecase: UserUseCase = Depends(get_user_usecases),
    auth_lock_service: AuthLockService = Depends(withdraw_auth_lock),
):
    withdrawal_request.authorization.ip_address = request.client.host
    withdrawal_request.authorization.user_agent = request.headers.get("user-agent")

    logger.info(
        "Withdrawal attempt for user %s, asset ID: %s, amount: %s, IP: %s, User-Agent: %s",
        user.get_prefixed_id(),
        withdrawal_request.asset_id,
        withdrawal_request.amount,
        withdrawal_request.authorization.ip_address,
        withdrawal_request.authorization.user_agent,
    )

    # Check if account is locked
    is_locked, err = await auth_lock_service.is_account_locked(user.email)
    if err or is_locked:
        logger.warning(
            "Account locked for user %s (email: %s) due to too many failed attempts. IP: %s, User-Agent: %s",
            user.id,
            user.email,
            withdrawal_request.authorization.ip_address,
            withdrawal_request.authorization.user_agent,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Account is locked due to too many failed attempts."},
        )

    # 1. Verify Transaction PIN
    valid, err = await user_usecase.verify_transaction_pin(
        user.id, withdrawal_request.authorization.pin
    )
    if err or not valid:
        current_attempts, _ = await auth_lock_service.increment_failed_attempts(
            user.email
        )
        logger.warning(
            "Invalid transaction PIN for user %s (email: %s). Failed attempts: %s. IP: %s, User-Agent: %s",
            user.id,
            user.email,
            current_attempts,
            withdrawal_request.authorization.ip_address,
            withdrawal_request.authorization.user_agent,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid transaction PIN"},
        )

    # Reset failed attempts on successful PIN verification
    await auth_lock_service.reset_failed_attempts(user.email)

    specific_withdrawal, err = withdrawal_request.destination.to_specific_event()
    if err:
        logger.error(
            "Invalid withdrawal request for user %s (email: %s): %s. IP: %s, User-Agent: %s",
            user.id,
            user.email,
            err.message,
            withdrawal_request.authorization.ip_address,
            withdrawal_request.authorization.user_agent,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"error": err.message}
        )

    data, err = await wallet_manager.initiate_withdrawal(
        user=user,
        withdrawal_request=withdrawal_request,
        specific_withdrawal=specific_withdrawal,
    )
    if err:
        logger.error(
            "Failed to initiate withdrawal for user %s (email: %s): %s. IP: %s, User-Agent: %s",
            user.id,
            user.email,
            err.message,
            withdrawal_request.authorization.ip_address,
            withdrawal_request.authorization.user_agent,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": err.message},
        )
    transaction_id = data.get("transaction_id")
    logger.info(
        "Withdrawal initiated successfully for user %s (email: %s), transaction ID: %s. IP: %s, User-Agent: %s",
        user.id,
        user.email,
        transaction_id,
        withdrawal_request.authorization.ip_address,
        withdrawal_request.authorization.user_agent,
    )

    rq_manager.get_queue().enqueue(
        process_withdrawal_task,
        ledger_config=config.ledger,
        paycrest_config=config.paycrest,
        blockrader_config=config.block_rader,
        user_id=user.id,
        pin=withdrawal_request.authorization.pin,
        transaction_id=transaction_id,
        wallet_name=config.block_rader.wallets.wallets[0].wallet_id,
        ledger_id=config.ledger.ledgers.ledgers[0].ledger_id,
    )

    logger.info(
        "Withdrawal processing initiated in background for user %s (email: %s), transaction ID: %s. IP: %s, User-Agent: %s",
        user.id,
        user.email,
        transaction_id,
        withdrawal_request.authorization.ip_address,
        withdrawal_request.authorization.user_agent,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Withdrawal processing initiated successfully."},
    )