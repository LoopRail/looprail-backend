from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    get_config,
    get_current_session,
    get_current_user,
    get_security_usecase,
    get_session_usecase,
    get_user_usecases,
    get_wallet_manager_usecase,
)
from src.api.dependencies.extra_deps import get_rq_manager
from src.dtos.wallet_dtos import ProcessWithdrawalRequest, WithdrawalRequest
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.redis import RQManager
from src.infrastructure.tasks.withdrawal_tasks import process_withdrawal_task
from src.models import Session, User
from src.usecases import (
    SecurityUseCase,
    SessionUseCase,
    UserUseCase,
    WalletManagerUsecase,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.post("/inititate-withdraw", status_code=status.HTTP_200_OK)
async def initiate_withdraw(
    req: WithdrawalRequest,
    user: User = Depends(get_current_user),
    wallet_manager: WalletManagerUsecase = Depends(get_wallet_manager_usecase),
):
    logger.info(
        "Initiating withdrawal for user %s, asset ID: %s, amount: %s",
        user.id,
        req.asset_id,
        req.amount,
    )
    specific_withdrawal, err = req.destination.to_specific_event()
    if err:
        logger.error(
            "Invalid withdrawal request for user %s: %s",
            user.get_prefixed_id(),
            err.message,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"error": err.message}
        )

    data, err = await wallet_manager.initiate_withdrawal(
        user=user, withdrawal_request=req, specific_withdrawal=specific_withdrawal
    )
    if err:
        logger.error(
            "Failed to initiate withdrawal for user %s: %s", user.id, err.message
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": err.message},
        )
    logger.info(
        "Withdrawal initiated successfully for user %s, transaction ID: %s",
        user.id,
        data.get("transaction_id"),
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": data},
    )


@router.post("/process-withdraw", status_code=status.HTTP_200_OK)
async def process_withraw_request(
    req: ProcessWithdrawalRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_current_session),
    config: Config = Depends(get_config),
    rq_manager: RQManager = Depends(get_rq_manager),
    security_usecase: SecurityUseCase = Depends(get_security_usecase),
    session_usecase: SessionUseCase = Depends(get_session_usecase),
    user_usecase: UserUseCase = Depends(get_user_usecases),
):
    logger.info(
        "Processing withdrawal request for user %s, transaction ID: %s",
        user.id,
        req.transaction_id,
    )

    # 1. Verify PKCE
    verified, err = await security_usecase.verify_pkce(
        req.challenge_id, req.code_verifier
    )
    if err or not verified:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid PKCE challenge or verifier"},
        )

    # 2. Verify Transaction PIN
    valid, err = await user_usecase.verify_transaction_pin(user.id, req.transation_pin)
    if err or not valid:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Invalid transaction PIN"},
        )

    # 3. Enqueue the task
    rq_manager.get_queue().enqueue(
        process_withdrawal_task,
        user_id=user.id,
        pin=req.transation_pin,
        config=config,
        transaction_id=req.transaction_id,
        wallet_name=config.block_rader.wallets.wallets[0].wallet_id,
        ledger_id=config.ledger.ledgers.ledgers[0].ledger_id,
    )

    logger.info(
        "Withdrawal processing initiated in background for user %s, transaction ID: %s",
        user.id,
        req.transaction_id,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Withdrawal processing initiated successfully."},
    )
