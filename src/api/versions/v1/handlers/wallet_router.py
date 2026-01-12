from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.api.dependencies import get_current_user, get_wallet_manager_usecase
from src.dtos import WithdrawalRequest
from src.infrastructure.logger import get_logger
from src.models import User
from src.usecases import WalletManagerUsecase

logger = get_logger(__name__)

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.post("/inititate-withdraw", status_code=status.HTTP_200_OK)
async def initiate_withdraw(
    req: WithdrawalRequest,
    user: User = Depends(get_current_user),
    wallet_manager: WalletManagerUsecase = Depends(get_wallet_manager_usecase),
):
    specific_withdrawal, err = req.destination.to_specific_event()
    if err:
        logger.error("Invalid withdrawal request: %s", err.message)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"error": err.message}
        )

    data, err = await wallet_manager.initiate_withdrawal(
        user=user, withdrawal_request=req, specific_withdrawal=specific_withdrawal
    )
    if err:
        logger.error("Failed to initiate withdrawal: %s", err.message)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": err.message},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": data},
    )


@router.post("/process-withdraw", status_code=status.HTTP_200_OK)
async def process_withraw_request():
    pass
